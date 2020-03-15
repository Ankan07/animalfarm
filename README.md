to create virtual environment for python
1. pip3 install virtualenv
2. virtualenv py38 -p python3.8 (or whatever u have)

whenever you want to work here, activate the virtual env (create it for the first time)
source py38/bin/activate


for first time running this project,
npm install
pip install -r Requirements.txt


to run the server locally,
sls wsgi serve

to deploy to lambda
sls deploy

follow this article for setting up serverless
https://medium.com/@Twistacz/flask-serverless-api-in-aws-lambda-the-easy-way-a445a8805028