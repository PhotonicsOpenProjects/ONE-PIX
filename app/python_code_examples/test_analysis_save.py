from onepix.Analysis import Analysis

# Load an existing reconstruction_results_*.json (interactive folder picker)
# and run the analysis pipeline on it.
an = Analysis(plot_result=True)

pipeline_steps = [
    ("snv", {}),
]

an.data_analysis(pipeline_steps=pipeline_steps)

an.save_analysis_results(filename="test_save_an.json", save_path="../Hypercubes")
