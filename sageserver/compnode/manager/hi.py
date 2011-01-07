from bson import BSON
from bson.son import SON
import os
print "Hello World!"
o = SON(t='stdout', b='hi!')
os.write(4, BSON.encode(o))
os.write(4, "sup dawg????")



