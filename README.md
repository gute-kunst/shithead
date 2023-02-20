# Shithead Card Game


## Development

create schema from model:
`python pyshithead/models/common/request_models.py outputfile ../client_py/shithead/request-schema.json`

create client models from schema:
`datamodel-codegen --input request-schema.json --output model.py`

## Ressources
https://websockets.readthedocs.io/en/stable/intro/tutorial1.html#prerequisites


https://github.com/kthwaite/fastapi-websocket-broadcast/blob/master/app.py
