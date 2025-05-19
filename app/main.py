from fastapi import FastAPI
import app.utils as f

appl = FastAPI()

@appl.get("/validate/{branch}")
def api_vector_validate_config_branch(branch: str):
    return f.vector_validate_config_branch(f.repo, branch)
