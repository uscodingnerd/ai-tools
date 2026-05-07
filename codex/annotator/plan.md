<proposed_plan>
**Random Annotator Flow**

**Summary**
- Provide a Tkinter annotator UI that shows a randomly selected sentence for annotating, stores each labelled sentence in memory (no database), and locks records after saving.
- Expose a second “Stats & Classifier” page that recalculates agreement strength, reruns a simple Naive Bayes classifier, and surfaces agreement metrics plus the latest classification results.

**Implementation**
1. **In-memory record pipeline**
   - Keep a predefined pool of sentences; each session displays one random text and lets the user choose annotator 1/2/3 and a label before saving.
   - “Save annotation” stores the text plus the chosen label for the selected annotator in an in-memory list, clears the inputs, and prevents re-editing that record.
   - Track per-record annotation dictionaries so downstream agreement calculations can include all annotators that have already provided labels for that sentence.

2. **Classifier & agreement stats**
   - Build a minimal Naive Bayes classifier (bag-of-words, Laplace smoothing) that retrains on the saved records and uses a deterministic 80/20 split for evaluation.
   - Agreement strength is defined per record as `max_votes / total_votes` among the annotated annotators, recalculated whenever the stats window refreshes.

3. **Tkinter UI**
   - First page shows the current random sentence, annotator selector, label dropdown, and “Save annotation” button; once saved, the sentence is locked and the user must generate another random sentence.
   - A “Show stats” button opens a second window listing all saved records (text snippet, resolved label, agreement) and the classifier’s latest prediction/confidence plus accuracy.
   - The stats window also has a “Rerun classifier” button that retrains/evaluates the model on the newest record set and updates the displayed stats accordingly.

**Test Plan**
- Run `py -3 annotator/app.py`, annotate a few sentences for different annotators without saving the same record twice, and ensure the UI resets after each save.
- Open the stats window, verify it shows every saved record’s resolved label/agreement and classifier accuracy/predictions, then click “Rerun classifier” to make sure values update even if the number of records changes.
- Restart the app to confirm it starts with no saved records and immediately shows a new random sentence for annotation.

**Assumptions**
- Tkinter is available on the system, and the extra window-based stats view is acceptable without a formal web UI.
- In-memory persistence is enough for this workflow (no disk/database writes).
- Sufficient random sentences can be hard-coded; the original CSV does not need to be loaded.
</proposed_plan>
