# mgenerate spec

This is a spec to add a new script `mgenerate` to the mtools family. It will generate structured, semi-random data according to a template document. The template can be specified directly as a command line argument or it can be a file. The format for the template argument is in JSON. Additional arguments to `mgenerate` specify how many documents should be inserted. The output is one JSON document per line, which can be piped to mongoimport.

> ##### Example
>     mgenerate <JSON or file> --num 10000 | mongoimport --port 27017
> 


## Parsing the JSON document

All values are taken literally, except for special $-prefixed values.

These values can be simple strings, or documents. Simple strings can be used if none of the additional options need to be specified. To customize the behavior of a command, use the document style.

    { "_id": "$command" }
    { "_id": { "$command": { <additional options> } } }

Note that we are writing JSON, so field names have to be strings, the quotes cannot be left out.

Some commands have a shortcut syntax, taking an array as their only value to the command key. This array syntax is always only syntactic sugar for their most common use case, and there is always a (more verbose) document-style syntax that will achieve the same. Each command section will specify exactly what the array-syntax means.
    
    { "_id": { "$command": [ <additional options> ] } }


### `$objectid`

Creates an ObjectId(). Alias is `$oid`.


> ##### Example
>     
>     { "_id" : "$objectid" }
> 
> This command replaces `"$objectid"` with a proper newly generated ObjectId.


#### Additional Parameters

None


### `$number`

Creates a random number.

> ##### Example
>     
>     { "age" : "$number" }
> 
> This command replaces `"$number"` with a uniformly random number between 0 and 100.


#### Additional Parameters


###### lower and upper bounds
`{ "$number" : {"min" : 500, "max" : 1000 } }` <br>

Generate a uniformly random number between the `min` and `max` values (both ends inclusive). Either parameter can be omitted, the fall-back is the default (0 for lower bound, 100 for upper bound). If `min` > `max`, the tool will throw an error.

#### Array Syntax
`{ "$number" : [ MIN, MAX ] }` <br>

Short form for `{ "$number" : {"min" : MIN, "max" : MAX } }`.



### `$datetime`

Creates a random date and time. Alias is `$date`.


> ##### Example
>     
>     { "_id" : "$datetime" }
> 
> This command replaces `"$datetime"` with a randomly generated date between Jan 1, 1970 0:00:00.000 (Epoch 0) and now. 


#### Additional Parameters


###### lower and upper bounds
`{ "$number" : {"min" : 1358831035, "max" : 1390367035 } }` <br>

Generate a random date and time between the `min` and `max` values (both ends inclusive).

`min` and `max` values can be epoch numbers (see example above). They can also be strings that can be parsed as date (and optionally time), e.g. "2013-05-12 13:30". Finally, `min` and `max` can be relative
time periods, for example `-2d` which means 2 days ago, or `+15y` which means 15 years in the future. These values are always relative to "now", the creation date. The full list of options is listed in the mtools hci.py module.


#### Array Syntax
`{ "$datetime" : [ MIN, MAX ] }` <br>

Short form for `{ "$datetime" : {"min" : MIN, "max" : MAX } }`.


### `$missing`

### `$choose`

### `$array`

### `$email`

### `$concat`

### `$geo`





