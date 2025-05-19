from fastapi import FastAPI
import app.utils as f

appl = FastAPI()

# todo: add read path from command line
va = f.VectorAgent("/mnt/d/dev/github/vector-agent/app/config.yaml")

@appl.get("/validate/{branch}")
def api_vector_validate_config_branch(branch: str):
    return va.validate_config_branch(branch)
