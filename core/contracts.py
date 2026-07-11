"""
Single source of truth for all data shapes flowing through the pipeline.
Every pipeline stage takes a Pydantic model in and returns a Pydantic model out.
No stage should pass raw dicts to another stage.
"""
