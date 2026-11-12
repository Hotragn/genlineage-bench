gen:
	datamodel-codegen --input api/openapi.yaml --input-file-type openapi --output client/models.py --output-model-type pydantic_v2.BaseModel --disable-timestamp --formatters black isort

test:
	python -m unittest discover -s tests -v
