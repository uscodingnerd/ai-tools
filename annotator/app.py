import math
import random
import re
import sqlite3
import tkinter as tk
from collections import Counter, defaultdict
from pathlib import Path
from tkinter import ttk, messagebox
try:
    from sklearn.metrics import classification_report as _classification_report
except ImportError:
    _classification_report = None

LABEL_OPTIONS = ("positive", "negative", "neutral", "sarcastic")
ANNOTATORS = ("annotator_1", "annotator_2", "annotator_3")
LABEL_PLACEHOLDER = "Select label"
SENTENCE_POOL = (
    "This movie was okay, not great.",
    "It works as expected.",
    "Not good at all.",
    "Fantastic — if you like disappointment.",
    "I hate how it performs.",
    "Oh sure, best idea ever.",
    "Great job!",
    "Perfect, just what I needed... not.",
    "Wow, that’s just unbelievable!",
    "Really disappointing.",
    "Absolutely fantastic experience!",
    "Great, another broken one.",
    "This is a waste of money.",
    "Average performance, nothing special.",
    "It’s fine, I guess.",
)

DB_FILE = Path(__file__).with_name("annotations.db")


def ensure_annotations_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS annotations (
            id INTEGER PRIMARY KEY,
            text TEXT NOT NULL,
            annotator_1 TEXT,
            annotator_2 TEXT,
            annotator_3 TEXT
        )
        """
    )


def next_record_id() -> int:
    with sqlite3.connect(DB_FILE) as conn:
        ensure_annotations_table(conn)
        cursor = conn.execute("SELECT MAX(id) FROM annotations")
        result = cursor.fetchone()
        max_id = result[0] if result and result[0] is not None else 0
        return max_id + 1


def insert_annotation(record_id: int, text: str, annotations: dict[str, str | None]) -> None:
    with sqlite3.connect(DB_FILE) as conn:
        ensure_annotations_table(conn)
        conn.execute(
            """
            INSERT OR REPLACE INTO annotations AS target
                (id, text, annotator_1, annotator_2, annotator_3)
            VALUES
                (:id, :text, :annotator_1, :annotator_2, :annotator_3)
            """,
            {
                "id": record_id,
                "text": text,
                "annotator_1": annotations.get("annotator_1"),
                "annotator_2": annotations.get("annotator_2"),
                "annotator_3": annotations.get("annotator_3"),
            },
        )


def fetch_db_records() -> list[tuple[int, str, dict[str, str | None]]]:
    with sqlite3.connect(DB_FILE) as conn:
        ensure_annotations_table(conn)
        cursor = conn.execute(
            "SELECT id, text, annotator_1, annotator_2, annotator_3 FROM annotations"
        )
        return [
            (
                row[0],
                row[1],
                {
                    ANNOTATORS[0]: row[2],
                    ANNOTATORS[1]: row[3],
                    ANNOTATORS[2]: row[4],
                },
            )
            for row in cursor.fetchall()
        ]



def tokenize(text: str) -> list[str]:
    """Simple whitespace tokenizer that keeps alphanumeric tokens."""
    return re.findall(r"\b\w+\b", text.lower())


def resolve_annotations(annotations: dict[str, str | None]) -> tuple[str | None, float]:
    """Return the majority label and agreement strength for a record."""
    votes = [label for label in annotations.values() if label]
    if not votes:
        return None, 0.0
    counts = Counter(votes)
    max_votes = max(counts.values())
    top_labels = sorted(label for label, count in counts.items() if count == max_votes)
    resolved = top_labels[0]
    agreement = max_votes / len(votes)
    return resolved, agreement


class SimpleNaiveBayes:
    """Minimal multinomial Naive Bayes classifier."""

    def __init__(self) -> None:
        self.class_priors: dict[str, float] = {}
        self.word_counts: dict[str, Counter[str]] = defaultdict(Counter)
        self.class_word_totals: dict[str, int] = defaultdict(int)
        self.vocab: set[str] = set()
        self.trained = False

    def train(self, data: list[tuple[str, str]]) -> None:
        self.class_priors.clear()
        self.word_counts = defaultdict(Counter)
        self.class_word_totals = defaultdict(int)
        self.vocab.clear()
        self.trained = False

        if not data:
            return

        label_counts = Counter()
        for text, label in data:
            label_counts[label] += 1
            tokens = tokenize(text)
            for token in tokens:
                self.word_counts[label][token] += 1
                self.class_word_totals[label] += 1
                self.vocab.add(token)

        total_docs = sum(label_counts.values())
        self.class_priors = {label: count / total_docs for label, count in label_counts.items()}
        self.trained = True

    def predict(self, text: str) -> tuple[str | None, float]:
        if not self.trained or not self.class_priors:
            return None, 0.0

        tokens = tokenize(text)
        label_scores: dict[str, float] = {}
        for label, prior in self.class_priors.items():
            score = math.log(prior or 1e-9)
            denom = self.class_word_totals[label] + max(1, len(self.vocab))
            for token in tokens:
                count = self.word_counts[label][token]
                score += math.log((count + 1) / denom)
            label_scores[label] = score

        best_label = max(label_scores, key=label_scores.get)
        max_score = label_scores[best_label]
        total = sum(math.exp(score - max_score) for score in label_scores.values())
        confidence = math.exp(max_score - max_score) / total if total > 0 else 0.0
        return best_label, confidence

    def evaluate(self, dataset: list[tuple[str, str]]) -> tuple[float, list[tuple[str, str]]] | None:
        if not self.trained or not dataset:
            return None
        predictions: list[tuple[str, str]] = []
        for text, actual in dataset:
            predicted, _ = self.predict(text)
            predictions.append((actual, predicted))
        accuracy = sum(1 for actual, predicted in predictions if actual == predicted) / len(predictions)
        return accuracy, predictions


class StatsWindow:
    def __init__(self, parent: tk.Tk, app: "AnnotatorApp") -> None:
        self.app = app
        self.window = tk.Toplevel(parent)
        self.window.title("Stats & Classifier")
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.classifier = SimpleNaiveBayes()
        self.record_predictions: dict[int, tuple[str | None, float]] = {}
        self.accuracy_var = tk.StringVar(value="N/A")
        self.total_var = tk.StringVar(value="0")
        self.num_texts_var = tk.StringVar(value="0")
        self.avg_agreement_var = tk.StringVar(value="N/A")
        self.create_widgets()
        self.update_stats()

    def create_widgets(self) -> None:
        header = ttk.Frame(self.window)
        header.pack(fill="x", padx=10, pady=(10, 5))
        ttk.Label(header, text="Total records:").grid(row=0, column=0, sticky="w")
        ttk.Label(header, textvariable=self.total_var).grid(row=0, column=1, sticky="w")
        ttk.Label(header, text="Unique texts:").grid(row=0, column=2, sticky="w", padx=(20, 0))
        ttk.Label(header, textvariable=self.num_texts_var).grid(row=0, column=3, sticky="w")
        ttk.Label(header, text="Average agreement:").grid(row=0, column=4, sticky="w", padx=(20, 0))
        ttk.Label(header, textvariable=self.avg_agreement_var).grid(row=0, column=5, sticky="w")
        ttk.Label(header, text="Classifier accuracy:").grid(row=0, column=6, sticky="w", padx=(20, 0))
        ttk.Label(header, textvariable=self.accuracy_var).grid(row=0, column=7, sticky="w")

        table_frame = ttk.Frame(self.window)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)
        columns = ("id", "text", "resolved", "prediction", "confidence", "agreement")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col.capitalize())
            self.tree.column(col, anchor="w")
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(table_frame, command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        report_frame = ttk.LabelFrame(self.window, text="Classification report")
        report_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.report_text = tk.Text(report_frame, height=8, wrap="word", state="disabled")
        self.report_text.pack(fill="both", expand=True, padx=5, pady=5)
        if _classification_report is None:
            self.update_report("Install scikit-learn to see the classification report.")

        footer = ttk.Frame(self.window)
        footer.pack(fill="x", padx=10, pady=(5, 10))
        ttk.Button(footer, text="Rerun classifier", command=self.update_stats).pack(side="left")

    def update_stats(self) -> None:
        raw_records = fetch_db_records()
        records = []
        agreements = []
        for rec_id, text, annotations in raw_records:
            resolved, agreement = resolve_annotations(annotations)
            records.append(
                {
                    "id": rec_id,
                    "text": text,
                    "resolved": resolved or "pending",
                    "agreement": agreement,
                }
            )
            if agreement:
                agreements.append(agreement)

        self.total_var.set(str(len(records)))
        unique_texts = {record["text"] for record in records}
        self.num_texts_var.set(str(len(unique_texts)))
        if agreements:
            avg = sum(agreements) / len(agreements)
            self.avg_agreement_var.set(f"{avg:.2%}")
        else:
            self.avg_agreement_var.set("N/A")

        dataset = [(rec["text"], rec["resolved"]) for rec in records if rec["resolved"] != "pending"]
        self.run_classifier(dataset, records)
        self.refresh_table(records)

    def run_classifier(self, dataset: list[tuple[str, str]], records: list[dict]) -> None:
        if not dataset:
            self.accuracy_var.set("N/A")
            self.record_predictions.clear()
            self.update_report("No labeled records yet.")
            return
        rnd = random.Random(42)
        rnd.shuffle(dataset)
        split = max(1, int(len(dataset) * 0.8))
        if split >= len(dataset):
            split = len(dataset) - 1 if len(dataset) > 1 else 1
        train_data = dataset[:split]
        test_data = dataset[split:] if dataset[split:] else train_data
        self.classifier.train(train_data)
        evaluation = self.classifier.evaluate(test_data)
        if evaluation:
            accuracy, predictions = evaluation
            self.accuracy_var.set(f"{accuracy:.2%}")
            y_true = [actual for actual, _ in predictions]
            y_pred = [pred for _, pred in predictions]
            if _classification_report:
                report = _classification_report(y_true, y_pred, zero_division=0)
            else:
                report = "scikit-learn not installed; install it to view the classification report."
            self.update_report(report)
        else:
            self.accuracy_var.set("N/A")
            self.update_report("Unable to evaluate the classifier with the current dataset.")

        self.record_predictions = {}
        for record in records:
            prediction = self.classifier.predict(record["text"])
            self.record_predictions[record["id"]] = prediction

    def refresh_table(self, records: list[dict]) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        for record in records:
            pred, conf = self.record_predictions.get(record["id"], (None, 0.0))
            snippet = record["text"]
            if len(snippet) > 60:
                snippet = snippet[:57] + "..."
            agreement = f"{record['agreement']:.2%}" if record["agreement"] else "N/A"
            self.tree.insert(
                "",
                "end",
                values=(
                    record["id"],
                    snippet,
                    record["resolved"],
                    pred or "—",
                    f"{conf:.2%}",
                    agreement,
                ),
            )

    def update_report(self, text: str) -> None:
        if not self.report_text:
            return
        self.report_text.configure(state="normal")
        self.report_text.delete("1.0", "end")
        self.report_text.insert("1.0", text)
        self.report_text.configure(state="disabled")

    def close(self) -> None:
        self.app.stats_window = None
        self.window.destroy()


class AnnotatorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("Multi-Annotator Sentiment")
        self.records: list[dict] = []
        self.record_counter = next_record_id()
        self.current_text: str | None = None
        self.stats_window: StatsWindow | None = None
        self.label_vars = {
            annotator: tk.StringVar(value=LABEL_PLACEHOLDER) for annotator in ANNOTATORS
        }
        self.label_options = (LABEL_PLACEHOLDER,) + LABEL_OPTIONS
        self.status_var = tk.StringVar(value="Generate a sentence to get started.")
        self.create_widgets()
        self.generate_sentence()

    def create_widgets(self) -> None:
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Current sentence:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.text_var = tk.StringVar()
        self.text_label = ttk.Label(frame, textvariable=self.text_var, wraplength=400, justify="left")
        self.text_label.pack(anchor="w", pady=(0, 10))

        label_frame = ttk.Frame(frame)
        label_frame.pack(fill="x", pady=5)
        for idx, annotator in enumerate(ANNOTATORS):
            ttk.Label(label_frame, text=f"{annotator.capitalize()}:").grid(row=idx, column=0, sticky="w")
            option = ttk.OptionMenu(
                label_frame,
                self.label_vars[annotator],
                self.label_vars[annotator].get(),
                *self.label_options,
            )
            option.grid(row=idx, column=1, sticky="w", padx=5, pady=2)
            self.label_vars[annotator].trace_add("write", lambda *args: self.update_save_button_state())

        button_frame = ttk.Frame(frame)
        button_frame.pack(fill="x", pady=(10, 5))
        self.save_button = ttk.Button(button_frame, text="Save annotation", command=self.save_annotation)
        self.save_button.pack(side="left")
        self.save_button.state(["disabled"])
        ttk.Button(button_frame, text="Generate sentence", command=self.generate_sentence).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Show stats", command=self.open_stats).pack(side="left", padx=5)

        ttk.Label(frame, textvariable=self.status_var, foreground="gray").pack(anchor="w", pady=(5, 0))

    def generate_sentence(self) -> None:
        self.current_text = random.choice(SENTENCE_POOL)
        self.text_var.set(self.current_text)
        for var in self.label_vars.values():
            var.set(LABEL_PLACEHOLDER)
        self.update_save_button_state()
        self.status_var.set("Annotate the sentence, choose a label for each annotator, and save.")

    def save_annotation(self) -> None:
        if not self.current_text:
            messagebox.showwarning("No sentence", "Please generate a sentence before saving.")
            return
        annotations = {}
        for annotator, var in self.label_vars.items():
            value = var.get()
            if value == LABEL_PLACEHOLDER:
                messagebox.showwarning("Missing label", "Please select a label for every annotator.")
                return
            annotations[annotator] = value
        record = {
            "id": self.record_counter,
            "text": self.current_text,
            "annotations": annotations,
        }
        insert_annotation(record["id"], record["text"], record["annotations"])
        self.records.append(record)
        self.record_counter += 1
        self.status_var.set(f"Saved record {record['id']} for all annotators.")
        self.save_button.state(["disabled"])
        self.current_text = None
        self.text_var.set("Record saved. Generate another sentence.")
        if self.stats_window:
            self.stats_window.update_stats()

    def update_save_button_state(self) -> None:
        if not self.current_text:
            self.save_button.state(["disabled"])
            return
        ready = all(var.get() != LABEL_PLACEHOLDER for var in self.label_vars.values())
        if ready:
            self.save_button.state(["!disabled"])
        else:
            self.save_button.state(["disabled"])

    def open_stats(self) -> None:
        if self.stats_window and self.stats_window.window.winfo_exists():
            self.stats_window.window.lift()
            self.stats_window.update_stats()
            return
        self.stats_window = StatsWindow(self.root, self)


def main() -> None:
    root = tk.Tk()
    AnnotatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
