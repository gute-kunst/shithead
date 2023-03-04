# Shithead Card Game


## Development

create schema from model in dir `server`:
`python pyshithead/models/common/request_models.py outputfile ../client_py/shithead/request-schema.json`

create client models from schema in dir `client_py`:
`datamodel-codegen --input shithead/request-schema.json --output shithead/model.py --use-default-kwarg`

## Ressources
https://websockets.readthedocs.io/en/stable/intro/tutorial1.html#prerequisites


https://github.com/kthwaite/fastapi-websocket-broadcast/blob/master/app.py
