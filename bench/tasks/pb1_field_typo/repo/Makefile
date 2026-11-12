gen:
	python -m grpc_tools.protoc -Iproto --python_out=gen proto/acct/v1/user.proto proto/acct/v1/team.proto

test:
	python -m unittest discover -s tests -v
