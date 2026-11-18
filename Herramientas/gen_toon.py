#!/usr/bin/env python3
"""Genera DitheringComic.shadergraph (URP Unlit) a partir de la plantilla 'Unlit Simple'
y de nodos de ejemplo de Shader Graph. Uso: gen_dithering.py <nodes.json> <plantilla> <salida>"""
import json, re, sys, uuid, copy

nodes_json, template_path, out_path = sys.argv[1:4]
T = json.load(open(nodes_json))  # tipo -> [archivo, nodo, slots]


def load(p):
    t = open(p, encoding='utf-8-sig').read()
    return [json.loads(x) for x in re.split(r'\n\n(?=\{)', t.strip())]


def nid():
    return uuid.uuid4().hex


objs = load(template_path)
# plantilla de Swizzle 'xy' (salida Vector2) tomada del ejemplo PostProcessHalfTone
_ht = load(sys.argv[4])
_htby = {o['m_ObjectId']: o for o in _ht}
_sw = next(o for o in _ht if o['m_Type'].endswith('.SwizzleNode'))
T['SwizzleNode'] = [None, _sw, [_htby[x['m_Id']] for x in _sw['m_Slots']]]
graph = objs[0]
by = {o['m_ObjectId']: o for o in objs}

# --- quitar HDRP / quedarnos solo con URP -----------------------------------
drop_types = ('HDTarget', 'HDUnlitSubTarget', 'SystemData', 'BuiltinData', 'HDUnlitData')
objs = [o for o in objs if o['m_Type'].split('.')[-1] not in drop_types]
by = {o['m_ObjectId']: o for o in objs}
graph['m_ActiveTargets'] = [t for t in graph['m_ActiveTargets'] if t['m_Id'] in by]
graph['m_Path'] = 'Proyecto Final'

# nodos existentes de la plantilla
def find(pred):
    return next(o for o in objs if pred(o))

mult_tex = find(lambda o: o['m_Type'].endswith('.MultiplyNode'))
base_color_block = find(lambda o: o.get('m_Name') == 'SurfaceDescription.BaseColor')
prop_color = find(lambda o: o['m_Type'].endswith('ColorShaderProperty'))
prop_tex = find(lambda o: o['m_Type'].endswith('Texture2DShaderProperty'))
category = find(lambda o: o['m_Type'].endswith('CategoryData'))
prop_color['m_Name'] = 'Color Base'
prop_color['m_RefNameGeneratedByDisplayName'] = 'Color Base'
prop_tex['m_Name'] = 'Textura'
prop_tex['m_RefNameGeneratedByDisplayName'] = 'Textura'

# quitar la conexión Multiply -> BaseColor (la reemplazamos por el Lerp)
graph['m_Edges'] = [e for e in graph['m_Edges']
                    if e['m_InputSlot']['m_Node']['m_Id'] != base_color_block['m_ObjectId']]

# mover nodos de la plantilla a la zona de "color"
def setpos(node, x, y):
    node['m_DrawState']['m_Position']['x'] = float(x)
    node['m_DrawState']['m_Position']['y'] = float(y)

for o in objs:
    if o['m_Type'].endswith('.PropertyNode') and o['m_Property']['m_Id'] == prop_tex['m_ObjectId']:
        setpos(o, -1150, 650)
    elif o['m_Type'].endswith('.PropertyNode') and o['m_Property']['m_Id'] == prop_color['m_ObjectId']:
        setpos(o, -900, 870)
    elif o['m_Type'].endswith('SampleTexture2DNode'):
        setpos(o, -950, 600)
    elif o is mult_tex:
        setpos(o, -700, 650)

new = []          # objetos nuevos


def add_node(kind, x, y, extra=None, slot_values=None, group=''):
    _, tpl, slots = T[kind]
    n = copy.deepcopy(tpl)
    n['m_ObjectId'] = nid()
    n['m_Group'] = {'m_Id': group}
    setpos(n, x, y)
    n['m_DrawState']['m_Position']['width'] = 0.0
    n['m_DrawState']['m_Position']['height'] = 0.0
    n['m_PreviewExpanded'] = True
    n['m_Slots'] = []
    for s in slots:
        s = copy.deepcopy(s)
        s['m_ObjectId'] = nid()
        if slot_values and s['m_Id'] in slot_values:
            s['m_Value'] = slot_values[s['m_Id']]
        n['m_Slots'].append({'m_Id': s['m_ObjectId']})
        new.append(s)
    if extra:
        n.update(extra)
    new.append(n)
    graph['m_Nodes'].append({'m_Id': n['m_ObjectId']})
    return n


def edge(a, aslot, b, bslot):
    graph['m_Edges'].append({
        'm_OutputSlot': {'m_Node': {'m_Id': a['m_ObjectId']}, 'm_SlotId': aslot},
        'm_InputSlot': {'m_Node': {'m_Id': b['m_ObjectId']}, 'm_SlotId': bslot}})


def add_float_prop(name, ref, value, lo=None, hi=None):
    _, tpl, _ = T['Vector1ShaderProperty']
    p = copy.deepcopy(tpl)
    p.update({'m_ObjectId': nid(), 'm_Guid': {'m_GuidSerialized': str(uuid.uuid4())},
              'm_Name': name, 'm_RefNameGeneratedByDisplayName': name,
              'm_DefaultReferenceName': '_' + name.replace(' ', '_'),
              'm_OverrideReferenceName': ref, 'm_Value': float(value)})
    p.setdefault('m_DismissedVersion', 0)
    p.setdefault('m_Precision', 0)
    p.setdefault('m_PerRendererData', False)
    p.setdefault('m_customAttributes', [])
    if lo is None:
        p['m_FloatType'] = 0
        p['m_RangeValues'] = {'x': 0.0, 'y': 1.0}
    else:
        p['m_FloatType'] = 1
        p['m_RangeValues'] = {'x': float(lo), 'y': float(hi)}
    new.append(p)
    graph['m_Properties'].append({'m_Id': p['m_ObjectId']})
    category['m_ChildObjectList'].append({'m_Id': p['m_ObjectId']})
    return p


def add_color_prop(name, ref, rgba):
    p = copy.deepcopy(prop_color)
    p.update({'m_ObjectId': nid(), 'm_Guid': {'m_GuidSerialized': str(uuid.uuid4())},
              'm_Name': name, 'm_RefNameGeneratedByDisplayName': name,
              'm_DefaultReferenceName': '_' + name.replace(' ', '_'),
              'm_OverrideReferenceName': ref,
              'm_Value': dict(zip('rgba', map(float, rgba)))})
    new.append(p)
    graph['m_Properties'].append({'m_Id': p['m_ObjectId']})
    category['m_ChildObjectList'].append({'m_Id': p['m_ObjectId']})
    return p


def prop_node(prop, x, y, group=''):
    """Nodo Property. La ranura de salida depende del tipo de propiedad."""
    _, tpl, slots = T['PropertyNode']
    n = copy.deepcopy(tpl)
    n['m_ObjectId'] = nid()
    n['m_Group'] = {'m_Id': group}
    setpos(n, x, y)
    n['m_Property'] = {'m_Id': prop['m_ObjectId']}
    s = copy.deepcopy(slots[0])
    s['m_ObjectId'] = nid()
    s['m_DisplayName'] = prop['m_Name']
    if prop['m_Type'].endswith('ColorShaderProperty'):
        s['m_Type'] = 'UnityEditor.ShaderGraph.Vector4MaterialSlot'
        s['m_Value'] = s['m_DefaultValue'] = {'x': 0.0, 'y': 0.0, 'z': 0.0, 'w': 0.0}
    n['m_Slots'] = [{'m_Id': s['m_ObjectId']}]
    new.append(s)
    new.append(n)
    graph['m_Nodes'].append({'m_Id': n['m_ObjectId']})
    return n


def group(title, x, y):
    _, g, _ = T['GroupData'] if 'GroupData' in T else (None, None, None)
    g = {'m_SGVersion': 0, 'm_Type': 'UnityEditor.ShaderGraph.GroupData',
         'm_ObjectId': nid(), 'm_Title': title, 'm_Position': {'x': float(x), 'y': float(y)}}
    new.append(g)
    graph['m_GroupDatas'].append({'m_Id': g['m_ObjectId']})
    return g['m_ObjectId']


def note(text, x, y, w=260, h=120, grp=''):
    s = {'m_SGVersion': 0, 'm_Type': 'UnityEditor.ShaderGraph.StickyNoteData',
         'm_ObjectId': nid(), 'm_Title': '', 'm_Content': text, 'm_TextSize': 0, 'm_Theme': 0,
         'm_Position': {'serializedVersion': '2', 'x': float(x), 'y': float(y),
                        'width': float(w), 'height': float(h)},
         'm_Group': {'m_Id': grp}}
    new.append(s)
    graph['m_StickyNoteDatas'].append({'m_Id': s['m_ObjectId']})


v2 = lambda x, y: {'x': float(x), 'y': float(y)}
v4 = lambda x, y=0, z=0, w=0: {'x': float(x), 'y': float(y), 'z': float(z), 'w': float(w)}

# --- Propiedades ----------------------------------------------------------------
p_tinta = add_color_prop('Color Tinta', '_ColorTinta', (0.05, 0.03, 0.08, 1))
p_dens = add_float_prop('Densidad de Puntos', '_DensidadPuntos', 70)
p_ang = add_float_prop('Angulo', '_Angulo', 45, 0, 90)
p_int = add_float_prop('Intensidad Puntos', '_IntensidadPuntos', 1.2, 0, 2)
p_umb = add_float_prop('Umbral Puntos', '_UmbralPuntos', 0.3, 0, 1)
p_sombra = add_color_prop('Color Sombra', '_ColorSombra', (0.45, 0.4, 0.6, 1))
p_bandas = add_float_prop('Bandas', '_Bandas', 3, 2, 6)
p_suav = add_float_prop('Suavizado', '_Suavizado', 0.08, 0.001, 0.5)

# ================= 1) Rejilla de puntos en pantalla ===========================
g1 = group('1) Rejilla de puntos en pantalla', -2900, -400)
scr_pos = add_node('ScreenPositionNode', -2850, -300, group=g1)              # Default (0..1)
swz = add_node('SwizzleNode', -2600, -300, group=g1)
screen = add_node('ScreenNode', -2850, -120, group=g1)
div_aspect = add_node('DivideNode', -2600, -120, group=g1)
comb = add_node('CombineNode', -2400, -120, slot_values={1: 1.0}, group=g1)     # (aspecto, 1)
mul_aspect = add_node('MultiplyNode', -2200, -300, group=g1)
p_ang_n = prop_node(p_ang, -2200, -60, group=g1)
rot = add_node('RotateNode', -1980, -300, extra={'m_Unit': 1},
               slot_values={1: v2(0, 0)}, group=g1)                             # grados, centro 0
p_dens_n = prop_node(p_dens, -1980, -60, group=g1)
mul_dens = add_node('MultiplyNode', -1750, -300, group=g1)
frac = add_node('FractionNode', -1540, -300, group=g1)
sub_half = add_node('SubtractNode', -1340, -300, slot_values={1: v4(0.5, 0.5, 0.5, 0.5)}, group=g1)
length = add_node('LengthNode', -1140, -300, group=g1)

edge(scr_pos, 0, swz, 0)
edge(screen, 0, div_aspect, 0)
edge(screen, 1, div_aspect, 1)
edge(div_aspect, 2, comb, 0)
edge(swz, 1, mul_aspect, 0)
edge(comb, 6, mul_aspect, 1)
edge(mul_aspect, 2, rot, 0)
edge(p_ang_n, 0, rot, 2)
edge(rot, 3, mul_dens, 0)
edge(p_dens_n, 0, mul_dens, 1)
edge(mul_dens, 2, frac, 0)
edge(frac, 1, sub_half, 0)
edge(sub_half, 2, length, 0)
note('Posición en pantalla corregida por el aspecto (para que las celdas sean cuadradas), '
     'rotada (ángulo clásico de cómic = 45°) y repetida con Fraction. Length da la distancia '
     'de cada píxel al centro de su celda: 0 en el centro, ~0.707 en las esquinas.',
     -2850, 0, 420, 110, g1)

# ================= 2) Iluminación (Half-Lambert) =============================
g2 = group('2) Luz principal (Half-Lambert)', -2900, 200)
normal = add_node('NormalVectorNode', -2850, 280, group=g2)                    # espacio mundo
light = add_node('MainLightDirectionNode', -2850, 420, group=g2)
dot = add_node('DotProductNode', -2600, 320, group=g2)
remap = add_node('RemapNode', -2380, 320,
                 slot_values={1: v2(-1, 1), 2: v2(0, 1)}, group=g2)            # D: 1 = oscuro, 0 = iluminado
edge(normal, 0, dot, 0)
edge(light, 0, dot, 1)
edge(dot, 2, remap, 0)
note('Main Light Direction apunta HACIA donde viaja la luz, así que N·dir = -1 en la cara iluminada; el Remap (-1..1 → 0..1) da: '
     'D = 0 en la cara iluminada y D = 1 en la cara en sombra. '
     'D alimenta a las bandas toon (3) y al tamaño de los puntos (4).',
     -2850, 560, 420, 100, g2)

# ================= 3) Bandas toon =============================================
g3 = group('3) Bandas toon (cel shading)', -2900, 750)
one_minus = add_node('OneMinusNode', -2850, 830, group=g3)                     # L = 1 - D
p_bandas_n = prop_node(p_bandas, -2850, 1000, group=g3)
mul_b = add_node('MultiplyNode', -2620, 830, group=g3)                         # L * Bandas
floor_n = add_node('FloorNode', -2400, 830, group=g3)                          # escalones enteros
sub_b = add_node('SubtractNode', -2620, 1000, slot_values={1: v4(1, 1, 1, 1)}, group=g3)  # Bandas - 1
div_b = add_node('DivideNode', -2180, 830, group=g3)                           # / (Bandas - 1)
sat_b = add_node('SaturateNode', -1960, 830, group=g3)                         # nivel toon 0..1
edge(remap, 3, one_minus, 0)
edge(one_minus, 1, mul_b, 0)
edge(p_bandas_n, 0, mul_b, 1)
edge(mul_b, 2, floor_n, 0)
edge(p_bandas_n, 0, sub_b, 0)
edge(floor_n, 1, div_b, 0)
edge(sub_b, 2, div_b, 1)
edge(div_b, 2, sat_b, 0)
note('Cuantiza la luz en escalones planos: floor(L·Bandas)/(Bandas-1). '
     'Con 3 bandas: sombra (0), medio tono (0.5) y luz (1).',
     -2850, 1120, 420, 80, g3)

# ================= 4) Máscara de puntos ======================================
g4 = group('4) Máscara de puntos (halftone)', -1000, -150)
p_umb_n = prop_node(p_umb, -1250, 120, group=g4)
sub_umb = add_node('SubtractNode', -1000, 60, group=g4)     # D - umbral
p_int_n = prop_node(p_int, -1000, 220, group=g4)
mul_int = add_node('MultiplyNode', -780, 60, group=g4)      # radio del punto
sub_r = add_node('SubtractNode', -560, -60, group=g4)       # distancia - radio
p_suav_n = prop_node(p_suav, -560, 160, group=g4)
div_s = add_node('DivideNode', -340, -60, group=g4)         # / suavizado
sat = add_node('SaturateNode', -120, -60, group=g4)         # 0 = tinta, 1 = papel
edge(remap, 3, sub_umb, 0)
edge(p_umb_n, 0, sub_umb, 1)
edge(sub_umb, 2, mul_int, 0)
edge(p_int_n, 0, mul_int, 1)
edge(length, 1, sub_r, 0)
edge(mul_int, 2, sub_r, 1)
edge(sub_r, 2, div_s, 0)
edge(p_suav_n, 0, div_s, 1)
edge(div_s, 2, sat, 0)
note('Radio = (D - Umbral) · Intensidad. Por debajo del umbral el radio es negativo y no hay '
     'puntos (zona iluminada limpia). Distancia < radio → tinta. Suavizado da el borde antialiasado.',
     -1000, 320, 440, 100, g4)

# ================= 5) Color final ============================================
g5 = group('5) Color final: toon + puntos', -450, 450)
p_sombra_n = prop_node(p_sombra, -420, 700, group=g5)
mul_sombra = add_node('MultiplyNode', -200, 650, group=g5)  # color base sombreado
lerp_toon = add_node('LerpNode', 20, 520, group=g5)         # bandas toon
p_tinta_n = prop_node(p_tinta, 20, 400, group=g5)
lerp = add_node('LerpNode', 250, 420, group=g5)             # puntos encima
edge(mult_tex, 2, mul_sombra, 0)
edge(p_sombra_n, 0, mul_sombra, 1)
edge(mul_sombra, 2, lerp_toon, 0)
edge(mult_tex, 2, lerp_toon, 1)
edge(sat_b, 1, lerp_toon, 2)
edge(p_tinta_n, 0, lerp, 0)
edge(lerp_toon, 3, lerp, 1)
edge(sat, 1, lerp, 2)
edge(lerp, 3, base_color_block, 0)
note('Primero el toon: Lerp entre (base × Color Sombra) y el color base según la banda. '
     'Después la tinta: los puntos se pintan encima con Color Tinta.',
     -420, 850, 420, 80, g5)

out = objs + new
with open(out_path, 'w', encoding='utf-8') as f:
    f.write('\n\n'.join(json.dumps(o, indent=4) for o in out) + '\n\n')

# --- validación básica -------------------------------------------------------
ids = {o['m_ObjectId'] for o in out}
def refs(x):
    if isinstance(x, dict):
        if set(x) == {'m_Id'} and isinstance(x['m_Id'], str) and x['m_Id']:
            yield x['m_Id']
        for v in x.values():
            yield from refs(v)
    elif isinstance(x, list):
        for v in x:
            yield from refs(v)
missing = [r for o in out for r in refs(o) if r not in ids]
print('objetos:', len(out), 'referencias rotas:', missing)
slot_ids = {o['m_ObjectId']: o for o in out}
for e in graph['m_Edges']:
    for side, want in (('m_OutputSlot', 1), ('m_InputSlot', 0)):
        node = slot_ids[e[side]['m_Node']['m_Id']]
        ok = any(slot_ids[s['m_Id']]['m_Id'] == e[side]['m_SlotId'] and slot_ids[s['m_Id']]['m_SlotType'] == want
                 for s in node['m_Slots'])
        if not ok:
            print('ARISTA MALA', node.get('m_Name'), side, e[side]['m_SlotId'])
