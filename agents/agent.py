from google.adk.apps import App
from google.adk.plugins.save_files_as_artifacts_plugin import SaveFilesAsArtifactsPlugin

# TODO: switch to the chate agent, once added in repo
from .model_agent import model_agent

root_agent = model_agent

app = App(
    name="agents",
    root_agent=root_agent,
    plugins=[SaveFilesAsArtifactsPlugin()]
)