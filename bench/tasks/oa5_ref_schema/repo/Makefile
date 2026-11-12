gen:
	datamodel-codegen --input schemas/customer.json --input-file-type jsonschema --output client/models.py --output-model-type pydantic_v2.BaseModel --disable-timestamp --formatters black isort

test:
	python -m unittest discover -s tests -v
