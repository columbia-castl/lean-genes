# server.py
from flask import Flask, request

hashes = []
app = Flask(__name__)
hashnum_provided = False
hashnum = 0

@app.route("/", methods = ['GET', 'PUT'])
def hash_store():
    global hashnum, hashnum_provided, hashes
    if request.method == 'PUT':
        if not hashnum_provided:
            hashnum = int(request.args['num_hashes'])
            hashnum_provided = True
            return "Hashnum provided."
        #TODO: send seqnums with the hashes or something of that nature
        elif len(hashes) < hashnum:
            hashes.append(str(request.get_data().decode()))
            print("received hash." + str(len(hashes)))
            return str(len(hashes))
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
                    print("looking at loc " + loc)
                    print(hashes[int(loc)] + " is stored hash")
                    print(len(hashes[int(loc)]))
                    print(str(request.args.get('hash')) + " is provided hash")
                    print(len(str(request.args.get('hash'))))
                    if hashes[int(loc)] == request.args.get('hash'):
                        found_string += str(loc) + ","
                
                print(request.args.get('locs') + " is locs.")
                print(request.args.get('hash') + " is hash.")

                if (found_string == ""):
                    found_string += "-1"

                print("returning: " + request.args.get('hash') + ": " + found_string)
                return request.args.get('hash') + ": " + found_string

            else:
                key = request.args['key']
                return hashes[int(key)]


app.run(port=80)
