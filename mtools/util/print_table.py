def print_table( rows, override_headers=None, uppercase_headers=True ):
    """ rows needs to be a list of dictionaries, all with the same keys. """
    
    keys = rows[0].keys()
    headers = override_headers or keys
    if uppercase_headers:
        rows = [ dict(zip(keys, map(lambda x: x.upper(), headers))), None ] + rows
    else:
        rows = [ dict(zip(keys, headers)), None ] + rows

    lengths = [ max( len(str(row[k])) for row in rows if hasattr(row, '__iter__') ) for k in keys ]
    template = (' '*4).join( ['{%s:%i}'%(h,l) for h,l in zip(keys, lengths)] )

    for row in rows:
        if type(row) == str:
            print row
        elif row == None:
            print
        else:
            print template.format(**row)


if __name__ == '__main__':

    d = [ {'a': '123', 'b': '654', 'c':'foo'},
          {'a': '12ooo3', 'b': '654', 'c':'foo'},
          {'a': '123', 'b': '65123124', 'c':'foo'},
          {'a': '123', 'b': '654', 'c':'fsadadsoo'},
          None,
          {'a': '123', 'b': '654', 'c':'foo'} ]

    print_table(d, ['long title here', 'foo', 'bar']) 
    
