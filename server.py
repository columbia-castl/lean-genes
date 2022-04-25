# server.py
from flask import Flask, request
import shelve
from waitress import serve

hashes = []
app = Flask(__name__)
hashnum_provided = False
hashnum = 0

dna_shelves = []
num_shelves = 24
in_shelf = 0

@app.route("/", methods = ['GET', 'PUT'])
def hash_store():
    global hashnum, hashnum_provided, hashes, in_shelf
    if request.method == 'PUT':
        if not hashnum_provided:
            hashnum = int(request.args['num_hashes'])
            hashnum_provided = True
            for i in range(num_shelves):
                dna_shelves.append(shelve.open('s' + str(i)))
            return "Hashnum provided."
        #TODO: send seqnums with the hashes or something of that nature
        elif len(hashes) < hashnum:
            #hashes.append(str(request.get_data().decode()))
            #print(request.json())
            for hash in request.json:
                dna_shelves[0][str(in_shelf)] = hash
            if (in_shelf % 10000 == 0):
                print("Received " + str(in_shelf) + " hashes")
            #print("received hash " + str(in_shelf))
            in_shelf += len(request.json)
            return str(in_shelf)
        else:
            print("out of place PUT request")
            return "All hashes received already."
    else:
        if (len(hashes) < hashnum) or (not hashnum_provided):
            print("hashnum is " + str(hashnum))
            print("len(hashes) is " + str(len(hashes)))
            return str(hashnum - len(hashes)) + " hashes still needed. Sorry."
        else:
            if (request.args.get('locs') != None):
                found_string = ""
                loc_list = request.args.get('locs').split(",")
                for loc in loc_list:
                    #print("looking at loc " + loc)
                    #print(hashes[int(loc)] + " is stored hash")
                    #print(len(hashes[int(loc)]))
                    #print(str(request.args.get('hash')) + " is provided hash")
                    #print(len(str(request.args.get('hash'))))
                    if hashes[int(loc)] == request.args.get('hash'):
                        found_string += str(loc) + ","
                
                #print(request.args.get('locs') + " is locs.")
                #print(request.args.get('hash') + " is hash.")

                if (found_string == ""):
                    found_string += "-1"

                #print("returning: " + request.args.get('hash') + ": " + found_string)
                return request.args.get('hash') + ": " + found_string

            else:
                key = request.args['key']
                return dna_shelves[0][key]


#app.run('0.0.0.0',port=80)
serve(app, host='127.0.0.1', port=4567)
