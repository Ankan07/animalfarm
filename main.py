from flask import Flask, render_template, request
from flask.json import JSONEncoder


from bson import json_util
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from http_error import invalidUsage
from pymongo import MongoClient
from pprint import pprint
from bson.json_util import dumps

import weaning
import trivial_display
import colony_handler as ch
import life_and_death as lnd

class CustomJSONEncoder(JSONEncoder):
    def default(self, obj): return json_util.default(obj)


app = Flask(__name__)
app.json_encoder = CustomJSONEncoder
client = MongoClient(
    "mongodb://krishnabose02:adminKrishna123@ec2-52-66-245-195.ap-south-1.compute.amazonaws.com:20202/admin?retryWrites=true&w=majority")
db = client.animalfarm


@app.route('/')
def hello_world():
    x = db.meta.find({})
    return dumps(x)

@app.route('/getColony', methods=['GET'])
def getColony():
    return trivial_display.getColony(db)

@app.route('/getBreeder', methods=['GET'])
def getBreeders():
    return trivial_display.getBreeders(db)

@app.route('/getBatch', methods=['GET'])
def getBatch():
    return trivial_display.getBatch(db)

@app.route('/getMS', methods=['GET'])
def getMS():
    return trivial_display.getMS(db)

@app.route('/v1/reportBirth', methods=['POST'])
def handle_request():
    return lnd.reportBirth(request.get_json(), db)


@app.route('/v1/reportDeath',methods=['POST'])
def reportDeath():
    lnd.reportDeath(request.get_json(), db)


@app.route('/v1/getContainerDetails', methods=['POST'])
def getDataFromQRCode():
    input = request.get_json()
    for x in ['type', 'id']:
        if x not in input:
            return invalidUsage(x + ' not found', 400)

    map = {
        'B' : 'breeder',
        'M' : 'market_selection',
        'S' : 'market_selection',
        'R' : 'undefined' # TODO this is still left, do something about it
    }
    if input['type'] not in map.keys():
        return invalidUsage('unrecognized type: ' + input['type'], 400)
    
    res = db[map[input['type']]].find_one({'_id': (input['id'])})
    if res == None:
        return invalidUsage('No container found with given ID', 404)
    return res

# This endpoint returns data related to a batch that is unweaned or partially weaned
@app.route('/v1/getWeaningData', methods=['POST'])
def getWeaningData():
    return weaning.getWeaningData(request.get_json(), db)


#  TODO, this method needs to be changed since the flow for weaning has changed
@app.route('/v1/addWeaningData', methods=['POST'])
def addWeaningData():
    return weaning.addWeaningData(request.get_json(), db)


# This endpoint is called when the weaning for a particular batch is complete
# This means, this batch has no unweaned neonates left, and can be removed from
# list of unweaned batches shown on the breeder page
@app.route('/v1/completeWeaning', methods=['POST'])
def completeWeaning():
    return weaning.completeWeaning(request.get_json(), db)

# This verifies the containers while they are being used for storing newly weaned animals
# This checks if this batch is previously partially weaned, and if so then whether the new
# box scanned is same as the previous box used (if any), and also, if a new box is scanned
# for a previously unused type, then check if that particular box is used anywhere else or not.
@app.route('/v1/verifyContainer', methods=['POST'])
def verifyContainer():
    return weaning.verifyContainer(request.get_json(), db)


@app.route('/v1/createColony',methods=['POST'])
def handle_create_colony():
    return ch.create_colony(request.get_json(), db)



# This verifies containers for creating a new colony
# Might need some modifications since the colony creation page underwent some changes
@app.route('/v1/verifyIdentity', methods=['POST'])
def verifyIdentity():
    return ch.verifyIdentity(request.get_json(), db)

if __name__ == '__main__':

    app.run('0.0.0.0', port=5000)
    # app.run()
