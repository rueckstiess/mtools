#!/usr/bin/env python3

def print_table(rows, override_headers=None, uppercase_headers=True):
    """All rows need to be a list of dictionaries, all with the same keys."""
    if len(rows) == 0:
        return
    keys = list(rows[0].keys())
    headers = override_headers or keys
    if uppercase_headers:
        rows = [dict(zip(keys,
                         map(lambda x: x.upper(), headers))), None] + rows
    else:
        rows = [dict(zip(keys, headers)), None] + rows

    lengths = [max(len(str(row[k]))
                   for row in rows if isinstance(row, dict)) for k in keys]
    tmp = ['{%s:%i}' % (h, l) for h, l in zip(keys[: -1], lengths[: -1])]
    tmp.append('{%s}' % keys[-1])
    template = (' ' * 4).join(tmp)

    for row in rows:
        if type(row) == str:
            print(row)
        elif row is None:
            print()
        elif isinstance(row, dict): 
            row = {k: v if v is not None else 'None' for k, v in row.items()}
            print(template.format(**row))
        else:
            print("Unhandled row type:", row)


if __name__ == '__main__':

    d = [{'a': '123', 'b': '654', 'c': 'foo'},
         {'a': '12ooo3', 'b': '654', 'c': 'foo'},
         {'a': '123', 'b': '65123124', 'c': 'foo'},
         {'a': '123', 'b': '654', 'c': 'fsadadsoo'},
         None,
         {'a': '123', 'b': '654', 'c': 'foo'}]

    print_table(d, ['long title here', 'foo', 'bar'])
