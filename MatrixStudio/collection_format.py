"""Generic collection records, with descriptions independent from generation prompts."""
import json
import unicodedata

ALIASES = {
    'id':'id', 'numero':'id', 'numeroimagen':'id', 'numerodeimagen':'id',
    'numerodeimagenenlacoleccion':'id', 'numeroenlacoleccion':'id', 'collectionid':'id',
    'titulo':'title', 'title':'title', 'nombre':'title', 'name':'title',
    'descripcion':'description', 'description':'description',
    'prompt':'prompt', 'promt':'prompt',
    'promptnegativo':'negative', 'promtnegativo':'negative', 'negativeprompt':'negative',
    'negative':'negative', 'negativo':'negative', 'promptnegativoopcional':'negative', 'promtnegativoopcional':'negative',
}


def normalized_key(key):
    text = unicodedata.normalize('NFKD', str(key)).casefold()
    return ''.join(c for c in text if c.isalnum())


def canonical_key(key):
    return ALIASES.get(normalized_key(key))


def compose_description(base, properties):
    parts = [base.strip()] if base.strip() else []
    for name, value in properties.items():
        rendered = value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2)
        parts.append(f'{name}: {rendered}')
    return '\n\n'.join(parts)


def parse_record(entry, index):
    if isinstance(entry,str):entry={'name':f'Imagen {index}','prompt':entry}
    if not isinstance(entry,dict):raise ValueError(f'Imagen {index}: se esperaba un objeto con ID, Titulo, Descripcion y Prompt.')
    fields, properties = {}, {}
    generic = any(normalized_key(key) in ('id','titulo','title','descripcion','description','promt') for key in entry)
    legacy_aliases={'numero':'id','nombre':'title','name':'title','negative':'negative','negativo':'negative'}
    primary_present={canonical_key(key) for key in entry if normalized_key(key) not in legacy_aliases and canonical_key(key)}
    for key,value in entry.items():
        field = canonical_key(key)
        if normalized_key(key) in legacy_aliases and field in primary_present:
            field=None
        if field:
            if field in fields and fields[field] != value:
                raise ValueError(f'Imagen {index}: el campo {field} aparece repetido con valores distintos.')
            fields[field]=value
        else:properties[key]=value
    if generic:
        required={'id':'ID','title':'Titulo','description':'Descripcion','prompt':'Prompt'}
        missing=[label for key,label in required.items() if key not in fields]
        if missing:raise ValueError(f'Imagen {index}: faltan {", ".join(missing)}.')
    identifier=fields.get('id',index)
    if type(identifier) not in (str,int) or not str(identifier).strip() or len(str(identifier))>80:
        raise ValueError(f'Imagen {index}: ID debe ser un entero o texto de hasta 80 caracteres.')
    title=fields.get('title',f'Imagen {index}')
    prompt=fields.get('prompt')
    base=fields.get('description','')
    if not isinstance(title,str) or not 1<=len(title.strip())<=120:raise ValueError(f'Imagen {index}: Titulo debe tener entre 1 y 120 caracteres.')
    if not isinstance(prompt,str) or not 1<=len(prompt.strip())<=12000:raise ValueError(f'Imagen {index}: Prompt debe tener entre 1 y 12000 caracteres.')
    if not isinstance(base,str):raise ValueError(f'Imagen {index}: Descripcion debe ser texto; puede ser una cadena vacía.')
    description=compose_description(base,properties)
    if len(description)>100000:raise ValueError(f'Imagen {index}: la descripción y sus propiedades superan 100000 caracteres.')
    item={'name':title.strip(),'prompt':prompt.strip(),'collection_id':identifier,
          'description_base':base.strip(),'description':description,'extra_properties':properties}
    if fields.get('negative') is not None:
        negative=fields['negative']
        if not isinstance(negative,str) or len(negative)>12000:raise ValueError(f'Imagen {index}: PromptNegativo debe ser texto de hasta 12000 caracteres.')
        item['negative']=negative
    legacy=None
    # Reimports of older records must enrich existing metadata instead of duplicating renders.
    old_title=entry.get('name',entry.get('nombre',f'Imagen {index}'))
    legacy_shape = not any(normalized_key(key) in ('id','titulo','title') for key in entry)
    if legacy_shape and isinstance(entry.get('prompt'),str) and isinstance(old_title,str) and old_title.strip():
        legacy={'name':old_title.strip(),'prompt':entry['prompt'].strip()}
        if 'negative_prompt' in entry or 'negative' in entry:
            value=entry.get('negative_prompt',entry.get('negative'))
            if isinstance(value,str):legacy['negative']=value
            else:legacy=None
        if legacy is not None:
            for key in ('numero','numero_pokedex'):
                if key in entry:legacy[key]=entry[key]
    return item,legacy


def migrate_collection_metadata(db):
    with db:
        for row in db.execute('SELECT id,params FROM renders').fetchall():
            p=json.loads(row['params'])
            if not p.get('image_batch_id') or 'collection_id' in p:continue
            identifier=p.get('numero')
            if identifier is None or not str(identifier).strip():identifier=p.get('batch_index',1)
            base=p.get('description_base',p.get('description',''))
            if not isinstance(base,str):base=''
            properties=dict(p.get('extra_properties') or {})
            if 'numero_pokedex' in p:properties.setdefault('numero_pokedex',p['numero_pokedex'])
            p.update(collection_id=identifier,description_base=base,description=compose_description(base,properties),extra_properties=properties)
            db.execute('UPDATE renders SET params=? WHERE id=?',(json.dumps(p,ensure_ascii=False),row['id']))
