from flask import Flask, render_template, request
from flask.json import JSONEncoder


from bson import json_util
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from http_error import InvalidUsage
from pymongo import MongoClient
from pprint import pprint

class CustomJSONEncoder(JSONEncoder):
    def default(self, obj): return json_util.default(obj)


app = Flask(__name__)
app.json_encoder = CustomJSONEncoder
client = MongoClient(
    "mongodb://krishnabose02:adminKrishna123@ec2-52-66-245-195.ap-south-1.compute.amazonaws.com:20202/admin?retryWrites=true&w=majority")
db = client.animalfarm


@app.route('/')
def hello_world():
    x = db.colony.find_one({"_id": ObjectId("5e517bd0443f2e2dd4d69bbb")})
    # y = db.colony.insert_one({"dummy": "data"})
    # print("y is ", y.inserted_id)
    return x


@app.route('/v1/reportBirth', methods=['POST'])
def handle_request():
    batch_json = request.get_json()
    batch_required_variables = ["dob",  "colonyId", "breed", "neocount", "breeder_id"]
    
    for x in batch_required_variables:
        if x not in batch_json:
            return InvalidUsage('Missing field: ' + x, 400)
    
    
    # adding parameters to batch
    
    batch_json["status"] = "neo"
    batch_json["dow"] = datetime.now() + timedelta(days=21)
    batch_json["count"] = batch_json["neocount"]
    
    batch_object = db.batch.insert_one(batch_json)

    task_json = {
        'created_At': datetime.now(),
        'colonyId': batch_json["colonyId"],
        'task': "Required Weaning",
        'status': "incomplete",
        "dueAt":datetime.now() + timedelta(days=21)
    }

    task_object = db.task.insert_one(task_json)

    upres = db.breeder.update({
        "_id": ObjectId(batch_json["breeder_id"])
    }, {
        '$push': {
            'batches': batch_object.inserted_id,
            'neonates': {
                'id': batch_object.inserted_id,
                'dob': batch_json['dob']
            }
        }
    })

    return {'status': 'true'} if (upres['acknowledged'] == True) else {'status': 'false'}

@app.route('/v1/getContainerDetails', methods=['POST'])
def getDataFromQRCode():
    input = request.get_json()
    for x in ['type', 'id']:
        if x not in input:
            return InvalidUsage(x + ' not found', 400)

    map = {
        'B' : 'breeder',
        'M' : 'market_selection',
        'S' : 'market_selection',
        'R' : 'undefined' # TODO this is still left, do something about it
    }
    if input['type'] not in map.keys():
        return InvalidUsage('unrecognized type: ' + input['type'], 400)
    
    res = db[map[input['type']]].find_one({'_id': ObjectId(input['id'])})
    if res == None:
        return InvalidUsage('No container found with given ID', 404)
    return res

@app.route('/v1/getWeaningData', methods=['POST'])
def getWeaningData():
    input = request.get_json()
    if 'id' not in input:
        return InvalidUsage('id not found!', 400)
    batchId = input['id']

    data = {}
    res = db.batch.find_one({'_id': ObjectId(batchId)})
    keys = ['mmboxId', 'mfboxId', 'smboxId', 'sfboxId']
    for k in keys:
        if k not in res:
            data[k] = 0
        else:
            smbox = db.market_selection.find_one({'_id': ObjectId(k)})
            data[k] = smbox['count']
    
    return data


@app.route('/v1/verifyContainer', methods=['POST'])
def verifyContainer():
    input_params = request.get_json()
    reqParams = ['batchId', 'colonyId', 'boxType', 'qr']
    for x in reqParams:
        if x not in input_params:
            return InvalidUsage('Missing field: ' + x, 400)
    
    for x in ['id', 'type']:
        if x not in input_params['qr']:
            return InvalidUsage('Missing field: ' + x, 400)
    qr = input_params['qr']
    # if this box was previously partial weaned, then match previous id with current id
    # if not previously weaned, then check if this box is used somewhere else

    # check box types
    type_map = {
        'mmboxId': 'M',
        'mfboxId': 'M',
        'smboxId': 'S',
        'sfboxId': 'S'
    }
    if input_params['boxType'] not in type_map:
        return {'isValid': False, 'message': input_params['boxType'] + ' not found in ' + str(type_map.keys())}
    if (type_map[input_params['boxType']] != qr['type']):
        return {'isValid': False}
    
    res = db.batch.find_one({'_id': ObjectId(input_params['batchId'])})
    if res != None:
        # previously weaned
        if input_params['boxType'] in res:
            # Some entry on this particular box type found, match with provided scanned box id
            existing_id = res[input_params['boxType']]
            if existing_id == qr['id']:
                # same box, return existing list
                msbox = db.market_selection.find_one({'_id': res[input_params['boxType']]})
                if msbox == None:
                    return InvalidUsage('The programmer messed it up, God bless him', 500)
                return {'isValid':True, 'weight': msbox.weight}
    
    # find if this box is used anywhere else
    res = db.market_selection.find_one({'_id': qr['id']})
    if res == None:
        # not used anywhere else, good to go
        return {'isValid': True, 'weight': []}
    
    # For every other condition, these boxes ain't loyal
    return {'isValid': False}

@app.route('/v1/addweaningdata', methods=['POST'])
def handle_request_two():
    input_params = request.get_json()
    print(input_params)

    required_variables = ["dob", "dow", "colonyId", "batchId", "gender",
                          "count", "weight", "wt_taken_at", "breed", "cname", "type", "scanned_id"]
    
    for x in required_variables:
        if x not in input_params:
            return InvalidUsage('Missing field: ' + x, 400)

    # verify market details
    # type should be any one of sfboxid,smboxid,mmboxid,mfboxid
    box_type = input_params["box_type"]
    scanned_id = input_params["scanned_id"]
    batch_id = input_params["batch_id"]
    type_box=input_params["type"]
    colony_id=input_params["colony_id"]

    market_selection_object = {
        "batch_id": input_params["batch_id"],
        "colony_id": input_params["colony_id"],
        "gender": input_params["gender"],
        "count": input_params["count"],
        "dob": input_params["dob"],
        "dow": input_params["dow"],
        "weight": input_params["weight"],
        "wt_taken_at": input_params["wt_taken_at"],
        "breed": input_params["breed"],
        "cname": input_params["cname"],
        "type": input_params["type"]
    }

    batch_object = db.batch.find_one({"_id": ObjectId(batch_id)})
    count=batch_object[count]# batch object current count
    if batch_object[box_type] == "": # check if box_type in batch is empty
        if db.market_selection.find({"_id": ObjectId(scanned_id)}).count() == 0: #check if market/selection box is not created
            insert_market_selection = db.market_selection.insert_one(market_selection_object) #insert a new m/s box
            new_count=count-input_params["count"] # update count value
            db.batch.update_one({"_id": ObjectId(batch_id)},{'$set':{type_box:insert_market_selection.inserted_id,"count":new_count}}) #insert the id into corresponding batch box and update count
            db.colony.update_one({"_id":ObjectId(colony_id)},{'$push': {"ms": insert_market_selection.inserted_id}}) # update ms array in colony id

    if batch_object[box_type]==scanned_id: #box is not empty (partial weaning)
        market_selection_box_existing = db.market_selection.find_one({"_id":ObjectId(scanned_id)}) #get existing box
        
        new_count=market_selection_box_existing["count"]+count -input_params["count"]
        db.batch.update_one({"_id": ObjectId(batch_id)},{'$set':{"count":new_count}}) #update count in batch object

        db.market_selection.update({"_id": ObjectId(scanned_id)},{'$set':market_selection_object}) #update the market_selection_box
             
              
@app.route('/v1/reportDeath',methods=['POST'])
def handle_request_three():
    input_params = request.get_json()

    reqparams = ['type', 'id', 'count']
    for x in reqparams:
        if x not in input_params:
            return InvalidUsage('Missing field: ' + x, 400)

    type_box = input_params["type"]
    box_id = input_params["id"]
    no_death = input_params["count"]

    # if the type_box is 'breeder' then there should be a 'death_type'
    # death_type should be neo, dame or sire

    if type_box == "market_selection":

        current = db.market_selection.find_one({"_id": ObjectId(box_id)})
        
        if current == None:
            return InvalidUsage('Invalid box scanned', 400)

        count = current["count"]
        if count - no_death < 0:
            return InvalidUsage('No of dead is more than total occupancy', 400)
        else:
            db.market_selection.update({
                "_id": ObjectId(box_id)
            }, {
                '$set': {
                    "count": count - no_death
                }
            })
            return {'status': 'true'}

    if type_box == "breeder":

        if 'death_type' not in input_params:
            return InvalidUsage('Missing field: death_type', 400)
        dtype = input_params['death_type']

        current = db.breeder.find_one({"_id": ObjectId(box_id)})

        if current == None:
            return InvalidUsage('Invalid box scanned', 400)

        if dtype == 'dame':

            count = current["ndames"]
            if count - no_death < 0:
                return InvalidUsage('Reported death of dames exceed the total count of dames', 400)
            else:
                db.breeder.update({
                    "_id": ObjectId(box_id)
                }, {
                    '$set': {
                        "ndames": count - no_death
                    }
                })
                return {'status': 'true'}
    
        if dtype == 'neo':

            # for neo, the batch_id should be sent too
            if 'batch_id' not in input_params:
                return InvalidUsage('Missing field: batch_id', 400)

            current = db.batch.find_one({"_id": ObjectId(input_params['batch_id'])})
            if current == None:
                return InvalidUsage('Invalid batch selected', 400)

            count = current["count"]
            if count - no_death < 0:
                return InvalidUsage('Reported death of neonates is larger than total count', 400)
            else:
                db.batch.update({
                    "_id": ObjectId(input_params['batch_id'])
                }, {
                    '$set': {
                        "count": count - no_death
                    }
                })
                return {'status': 'true'}





if __name__ == '__main__':

    app.run()
