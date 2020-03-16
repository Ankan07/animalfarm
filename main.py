from flask import Flask, render_template, request
from flask.json import JSONEncoder


from bson import json_util
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from http_error import invalidUsage
from pymongo import MongoClient
from pprint import pprint
from bson.json_util import dumps

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
    res = db.colony.find({})
    cols = []
    if res is None:
        return {'message': 'nothing found!'}
    for d in res:
        cols.append(d)
    return dumps(cols)

@app.route('/getBreeder', methods=['GET'])
def getBreeders():
    res = db.breeder.find({})
    cols = []
    if res is None:
        return {'message': 'nothing found!'}
    for d in res:
        cols.append(d)
    return dumps(cols)

@app.route('/getBatch', methods=['GET'])
def getBatch():
    res = db.batch.find({})
    cols = []
    if res is None:
        return {'message': 'nothing found!'}
    for d in res:
        cols.append(d)
    return dumps(cols)

@app.route('/getMS', methods=['GET'])
def getMS():
    res = db.market_selection.find({})
    cols = []
    if res is None:
        return {'message': 'nothing found!'}
    for d in res:
        cols.append(d)
    return dumps(cols)

@app.route('/v1/reportBirth', methods=['POST'])
def handle_request():
    batch_json = request.get_json()
    batch_required_variables = ["dob",  "colonyId", "breed", "neocount", "breederId"]
    
    for x in batch_required_variables:
        if x not in batch_json:
            return invalidUsage('Missing field: ' + x, 400).to_dict()
    
    
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
        "_id": (batch_json["breederId"])
    }, {
        '$push': {
            'batches': str(batch_object.inserted_id),
            'neonates': {
                'batchId': str(batch_object.inserted_id),
                'dob': batch_json['dob']
            }
        }
    })

    return {'status': 'true'} if (upres['updatedExisting'] == True) else {'status': 'false'}

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

@app.route('/v1/getWeaningData', methods=['POST'])
def getWeaningData():
    input = request.get_json()
    if 'id' not in input:
        return invalidUsage('id not found!', 400)
    batchId = input['id']

    data = {}
    res = db.batch.find_one({'_id': ObjectId(batchId)})
    if res is None:
        return invalidUsage('invalid batch', 403)
    keys = ['mmboxId', 'mfboxId', 'smboxId', 'sfboxId']
    #print(res)
    for k in keys:
        if k not in res:
            #print(k + ' not in res')
            data[k] = 0
        else:
            #print('trying to get ' + k)
            smbox = db.market_selection.find_one({'_id': (res[k])})
            if smbox is None:
                return invalidUsage('selection/male box is none for: ' + res[k], 500)
            data[k] = smbox['count']
    
    return data


@app.route('/v1/addWeaningData', methods=['POST'])
def addWeaningData():
    input_params = request.get_json()
    reqParams = ['weight', 'type', 'containerId', 'batchId']
    for x in reqParams:
        if x not in input_params:
            return invalidUsage('Missing field: ' + x, 400)
    
    # add data to batch
    # create a market_selection document with containerId
    res = db.batch.update_one({'_id': ObjectId(input_params['batchId'])}, {'$set': {
        input_params['type']: input_params['containerId']
    }})

    if res is None:
        return invalidUsage('something seriously went wrong', 500)
    # #print(res['raw_result'])
    res = db.batch.find_one({'_id': ObjectId(input_params['batchId'])})
    if res is None:
        return invalidUsage('batch not found, what on earth is happening?', 500)
    res = db.market_selection.update_one({'_id': input_params['containerId']},
    {
        '$set': {
        'batchId': input_params['batchId'],
        'colonyId': res['colonyId'],
        'gender': input_params['type'][1],
        'count': len(input_params['weight']),
        'dob': res['dob'],
        'dow': str(datetime.now()),
        'weight': [x['value'] for x in input_params['weight']],
        'weight_taken_at': str(datetime.now())
    }}, upsert=True)

    if res is None:
        return invalidUsage('failed to write to database', 500)
    
    return {'status': True}

@app.route('/v1/completeWeaning', methods=['POST'])
def completeWeaning():
    input_params = request.get_json()
    reqparams = ['breederId', 'batchId']
    for x in reqparams:
        if x not in input_params:
            return invalidUsage('Missing field: ' + x, 400)
    res = db.breeder.update_one({'_id': input_params['breederId']}, {
        '$pull': {
            'neonates': {'batchId':input_params['batchId']}
        }
    })
    if res is None:
        return invalidUsage('writing to database failed', 500)
    #print(res.raw_result)
    return {'status': True}

@app.route('/v1/verifyContainer', methods=['POST'])
def verifyContainer():
    input_params = request.get_json()
    reqParams = ['batchId', 'colonyId', 'boxType', 'qr']
    for x in reqParams:
        if x not in input_params:
            return invalidUsage('Missing field: ' + x, 400)
    
    for x in ['id', 'type']:
        if x not in input_params['qr']:
            return invalidUsage('Missing field: ' + x, 400)
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
                    return invalidUsage('The programmer messed it up, God bless him', 500)
                return {'isValid':True, 'weight': msbox['weight']}
            else:
                return {'isValid': False}
    # find if this box is used anywhere else
    res = db.market_selection.find_one({'_id': qr['id']})
    if res == None:
        # not used anywhere else, good to go
        return {'isValid': True, 'weight': []}
    
    # For every other condition, these boxes ain't loyal
    return {'isValid': False}

            
@app.route('/v1/reportDeath',methods=['POST'])
def handle_request_three():
    input_params = request.get_json()

    reqparams = ['type', 'id', 'count']
    for x in reqparams:
        if x not in input_params:
            return invalidUsage('Missing field: ' + x, 400)

    type_box = input_params["type"]
    box_id = input_params["id"]
    no_death = input_params["count"]

    # if the type_box is 'breeder' then there should be a 'death_type'
    # death_type should be neo, dame or sire

    if type_box == "market_selection":

        current = db.market_selection.find_one({"_id": (box_id)})
        
        if current == None:
            return invalidUsage('Invalid box scanned', 400)

        count = current["count"]
        if count - no_death < 0:
            return invalidUsage('No of dead is more than total occupancy', 400)
        else:
            db.market_selection.update({
                "_id": (box_id)
            }, {
                '$set': {
                    "count": count - no_death
                }
            })
            return {'status': 'true'}

    if type_box == "breeder":

        if 'death_type' not in input_params:
            return invalidUsage('Missing field: death_type', 400)
        dtype = input_params['death_type']

        current = db.breeder.find_one({"_id": (box_id)})

        if current == None:
            return invalidUsage('Invalid box scanned', 400)

        if dtype == 'dame':

            count = current["ndames"]
            if count - no_death < 0:
                return invalidUsage('Reported death of dames exceed the total count of dames', 400)
            else:
                db.breeder.update({
                    "_id": (box_id)
                }, {
                    '$set': {
                        "ndames": count - no_death
                    }
                })
                return {'status': 'true'}
    
        if dtype == 'neo':

            # for neo, the batch_id should be sent too
            if 'batch_id' not in input_params:
                return invalidUsage('Missing field: batch_id', 400)

            current = db.batch.find_one({"_id": ObjectId(input_params['batch_id'])})
            if current == None:
                return invalidUsage('Invalid batch selected', 400)

            count = current["count"]
            if count - no_death < 0:
                return invalidUsage('Reported death of neonates is larger than total count', 400)
            else:
                db.batch.update({
                    "_id": ObjectId(input_params['batch_id'])
                }, {
                    '$set': {
                        "count": count - no_death
                    }
                })
                return {'status': 'true'}

@app.route('/v1/createcolony',methods=['POST'])
def handle_create_colony():
    input_params = request.get_json()
    reqparams = ['sireId', 'breeder_ids','sire_batchId','sire_colonyId','colonyname']
    for x in reqparams:
        if x not in input_params:
            return invalidUsage('Missing field: ' + x, 400)

    #define the colony_object
    colony={}
    #get the current colony number.
    colony_number=db.meta.find_one({"type":"colonycount"})
    count=colony_number["count"]
    #increase colony count
    db.meta.update_one({"type":"colonycount"},{'$set':{'count':count+1}})
    #generate colony name
    colonyId='C'+str(count)
    colonyname=input_params['colonyname']
    #fetch selection_box_sire_details step 1
    sire_details=db.market_selection.find_one({"_id": input_params['sireId']})

    sire_batchId=input_params['sire_batchId']
    sire_colonyId=input_params['sire_colonyId']

    #creating the breeder object step 2
    breeder_ids=input_params['breeder_ids']
    for i in range(len(breeder_ids)):
        breeder_object={}
        temp=breeder_ids[i]
        breederId=temp["breederId"]



       
        breeder_object["dames"]=temp["dames"]
        breeder_object["ndames"]=len(breeder_object["dames"])
        breeder_object["neonates"]=[]
        breeder_object["_id"]=breederId
        breeder_object["ms"]=[]
        breeder_object["colonyId"]=colonyId
        breeder_object["cName"]=colonyname
   
        breeder_object["breed"]=sire_details["breed"]
        db.breeder.insert_one(breeder_object)
    
    #insering colony object
    sire={}
    sire["colonyId"]= sire_colonyId
    sire["batchId"]=sire_batchId
    colony["name"]=colonyname
    colony["sire"]=sire
    colony["generation"]=0
    colony["breeders"]=[x['breederId'] for x in breeder_ids]
    colony["ms"]=[]
    colony["rest"]=False
    colony["breed"]=sire_details["breed"]
 
    db.colony.insert_one(colony)

    return {'status':"success"}



   
    







if __name__ == '__main__':

    app.run()
