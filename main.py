from flask import Flask, render_template

from flask import request

from pymongo import MongoClient
from pprint import pprint

from flask.json import JSONEncoder

from bson import json_util
from datetime import datetime
from bson.objectid import ObjectId
from datetime import timedelta 

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
    y = db.colony.insert_one({"dummy": "data"})
    print("y is ", y.inserted_id)
    return x


@app.route('/v1/reportbirth', methods=['POST'])
def handle_request():
    batch_json = request.get_json()
    print(batch_json)
    batch_required_variables = ["dob",  "colonyId", "breed",
                                   "neocount", "breeder_id"]
    exception = False
    exception_parameter = ""
    for i in range(len(batch_required_variables)):
        if batch_required_variables[i] in batch_json:
            print("present")
        else:
            exception = True
            exception_parameter = batch_required_variables[i]
            break
    #print("exception parameter is ",exception_parameter)
    if exception == True:
        return {"message": "parameters missing", "status": "error"}
    else:

        # adding parameters to batch
       
        batch_json["status"]="neo"
        batch_json["dow"]=datetime.now()+timedelta(days=21)
        batch_json["count"]=batch_json["neocount"]
        
        
        batch_object = db.batch.insert_one(batch_json)

        task_json = {'created_At': datetime.now(), 'colonyId': batch_json["colonyId"], 'task': "Required Weaning", 'status': "incomplete","dueAt":datetime.now()+timedelta(days=21) }
        task_object = db.task.insert_one(task_json)
        db.breeder.update({"_id": ObjectId(batch_json["breeder_id"])}, {
                          '$push': {"batches": batch_object.inserted_id}})

        return "inserted"


@app.route('/v1/addweaningdata', methods=['POST'])
def handle_request_two():
    input_params = request.get_json()
    print(input_params)

    required_variables = ["dob", "dow", "colonyId", "batchId", "gender",
                          "count", "weight", "wt_taken_at", "breed", "cname", "type", "scanned_id"]
    exception = False
    exception_parameter = ""
    for i in range(len(required_variables)):
        if required_variables[i] in batch_json:
            print("present")
        else:
            exception = True
            exception_parameter = batch_required_variables[i]
            break
    #print("exception parameter is ",exception_parameter)
    if exception == True:
        return {"message": "parameters missing", "status": "error"}

    else:
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

        else if batch_object[box_type]==scanned_id: #box is not empty (partial weaning)
               market_selection_box_existing = db.market_selection.find_one({"_id":ObjectId(scanned_id)}) #get existing box
               
               new_count=market_selection_box_existing["count"]+count -input_params["count"]
               db.batch.update_one({"_id": ObjectId(batch_id)},{'$set':{"count":new_count}}) #update count in batch object

               db.market_selection.update({"_id": ObjectId(scanned_id)},{'$set':market_selection_object}) #update the market_selection_box
             
              


if __name__ == '__main__':

    app.run()
