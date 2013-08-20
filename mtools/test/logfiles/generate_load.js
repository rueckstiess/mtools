print('--- insert 1M')
for (var i=0; i<1000000; i++) { 
	db.docs.insert({number: i});
}
print('--- insert 1k')
for (var i=0; i<1000; i++) {
	db.docs.insert({number: i, payload: new Array(1024*1024).join('x')}, {'w': 'majority'});
}
print('--- build index')
db.docs.ensureIndex({number: 1})
db.docs.dropIndexes()
db.docs.ensureIndex({number:1}, {unique:true})
print('--- find+sort')
db.docs.find({number: {'$lt': 20000}}).sort({number: -1})
print('--- update')
for (var i=0; i<10; i++) {
	db.docs.update({number: i}, {number: i, payload: new Array(1024*1024).join('x')});
}
print('--- remove')
db.docs.remove({})
db.dropDatabase()
print('--- shutdown')
db.shutdownServer()
