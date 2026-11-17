"""Utilidades comunes para generar archivos .shadergraph (URP Unlit) desde Python.

Los nodos se clonan de ejemplos reales del paquete Shader Graph (nodes.json, generado con
collect.py), así el JSON resultante es válido para Unity 6000.5 / Shader Graph 17.5.
"""
import copy
import json
import os
import re
import uuid

AQUI = os.path.dirname(os.path.abspath(__file__))
PROYECTO = os.path.dirname(AQUI)
SG_PKG = next(os.path.join(PROYECTO, 'Library/PackageCache', d)
              for d in os.listdir(os.path.join(PROYECTO, 'Library/PackageCache'))
              if d.startswith('com.unity.shadergraph@'))
PLANTILLA = os.path.join(SG_PKG, 'GraphTemplates/Cross Pipeline/Unlit Simple.shadergraph')
HALFTONE = os.path.join(SG_PKG, 'Samples~/ProductionReady/PostProcess/PostProcessHalfTone.shadergraph')
EDGE = os.path.join(SG_PKG, 'Samples~/ProductionReady/PostProcess/PostProcessEdgeDetection.shadergraph')

SLOT = 'UnityEditor.ShaderGraph.'


def cargar(p):
    t = open(p, encoding='utf-8-sig').read()
    return [json.loads(x) for x in re.split(r'\n\n(?=\{)', t.strip())]


def nid():
    return uuid.uuid4().hex


def v2(x, y):
    return {'x': float(x), 'y': float(y)}


def v4(x, y=None, z=None, w=None):
    y = x if y is None else y
    z = x if z is None else z
    w = x if w is None else w
    return {'x': float(x), 'y': float(y), 'z': float(z), 'w': float(w)}


class Grafo:
    def __init__(self, ruta_menu, con_textura=True, pantalla=False):
        self.T = json.load(open(os.path.join(AQUI, 'nodes.json')))
        ht = cargar(HALFTONE)
        htby = {o['m_ObjectId']: o for o in ht}
        sw = next(o for o in ht if o['m_Type'].endswith('.SwizzleNode'))
        self.T['SwizzleNode'] = [None, sw, [htby[x['m_Id']] for x in sw['m_Slots']]]
        if pantalla:
            self._init_pantalla(ruta_menu)
            return

        objs = cargar(PLANTILLA)
        quitar = ('HDTarget', 'HDUnlitSubTarget', 'SystemData', 'BuiltinData', 'HDUnlitData')
        objs = [o for o in objs if o['m_Type'].split('.')[-1] not in quitar]
        self.objs = objs
        by = {o['m_ObjectId']: o for o in objs}
        g = self.g = objs[0]
        g['m_ActiveTargets'] = [t for t in g['m_ActiveTargets'] if t['m_Id'] in by]
        g['m_Path'] = ruta_menu

        f = lambda p: next(o for o in objs if p(o))
        self.target = f(lambda o: o['m_Type'].endswith('.UniversalTarget'))
        self.subtarget = f(lambda o: o['m_Type'].endswith('UniversalUnlitSubTarget'))
        self.mult_tex = f(lambda o: o['m_Type'].endswith('.MultiplyNode'))
        self.base_color = f(lambda o: o.get('m_Name') == 'SurfaceDescription.BaseColor')
        self.vert_pos = f(lambda o: o.get('m_Name') == 'VertexDescription.Position')
        self.prop_color = f(lambda o: o['m_Type'].endswith('ColorShaderProperty'))
        self.prop_tex = f(lambda o: o['m_Type'].endswith('Texture2DShaderProperty'))
        self.categoria = f(lambda o: o['m_Type'].endswith('CategoryData'))
        self.prop_color.update({'m_Name': 'Color Base', 'm_RefNameGeneratedByDisplayName': 'Color Base'})
        self.prop_tex.update({'m_Name': 'Textura', 'm_RefNameGeneratedByDisplayName': 'Textura'})
        g['m_Edges'] = [e for e in g['m_Edges']
                        if e['m_InputSlot']['m_Node']['m_Id'] != self.base_color['m_ObjectId']]
        self.nuevos = []
        if not con_textura:
            self._quitar_textura()

    def _init_pantalla(self, ruta_menu):
        """Grafo URP Fullscreen (para Full Screen Pass Renderer Feature), basado en el
        ejemplo PostProcessEdgeDetection pero sin ninguno de sus nodos."""
        src = cargar(EDGE)
        by = {o['m_ObjectId']: o for o in src}
        g = self.g = src[0]
        conservar = ('UniversalTarget', 'UniversalFullscreenSubTarget', 'FullscreenData')
        bloques = [by[b['m_Id']] for b in g['m_FragmentContext']['m_Blocks']]
        objs = [g] + [o for o in src if o['m_Type'].split('.')[-1] in conservar]
        for b in bloques:
            objs.append(b)
            objs += [by[s['m_Id']] for s in b['m_Slots']]
        self.categoria = {'m_SGVersion': 0, 'm_Type': SLOT + 'CategoryData', 'm_ObjectId': nid(),
                          'm_Name': '', 'm_ChildObjectList': []}
        objs.append(self.categoria)
        self.objs = objs
        g.update({'m_Properties': [], 'm_Keywords': [], 'm_Dropdowns': [],
                  'm_CategoryData': [{'m_Id': self.categoria['m_ObjectId']}],
                  'm_Nodes': [{'m_Id': b['m_ObjectId']} for b in bloques],
                  'm_GroupDatas': [], 'm_StickyNoteDatas': [], 'm_Edges': [],
                  'm_Path': ruta_menu})
        g['m_FragmentContext']['m_Position'] = v2(2600, 0)
        g['m_VertexContext']['m_Position'] = v2(2600, -100)
        self.target = next(o for o in objs if o['m_Type'].endswith('.UniversalTarget'))
        self.base_color = next(b for b in bloques if b['m_Name'] == 'SurfaceDescription.BaseColor')
        self.alpha = next(b for b in bloques if b['m_Name'] == 'SurfaceDescription.Alpha')
        # plantilla de propiedad de color (no se registra)
        self.prop_color = next(o for o in src if o['m_Type'].endswith('ColorShaderProperty'))
        self.mult_tex = None
        self.nuevos = []

    # ------------------------------------------------------------------ util
    @staticmethod
    def pos(n, x, y):
        n['m_DrawState']['m_Position']['x'] = float(x)
        n['m_DrawState']['m_Position']['y'] = float(y)

    def nodos_plantilla(self, tipo):
        return [o for o in self.objs if o['m_Type'].endswith('.' + tipo)]

    def nodo_prop_plantilla(self, prop):
        return next(o for o in self.objs if o['m_Type'].endswith('.PropertyNode')
                    and o['m_Property']['m_Id'] == prop['m_ObjectId'])

    def _quitar_textura(self):
        """Deja solo la propiedad Color (sin textura ni multiply)."""
        fuera = {self.mult_tex['m_ObjectId'], self.prop_tex['m_ObjectId']}
        for o in self.objs:
            if o['m_Type'].endswith('SampleTexture2DNode'):
                fuera.add(o['m_ObjectId'])
            if o['m_Type'].endswith('.PropertyNode'):
                fuera.add(o['m_ObjectId'])
        for o in list(self.objs):
            if o['m_ObjectId'] in fuera:
                fuera.update(s['m_Id'] for s in o.get('m_Slots', []))
        self.objs = [o for o in self.objs if o['m_ObjectId'] not in fuera]
        g = self.g
        g['m_Nodes'] = [n for n in g['m_Nodes'] if n['m_Id'] not in fuera]
        g['m_Properties'] = [p for p in g['m_Properties'] if p['m_Id'] not in fuera]
        self.categoria['m_ChildObjectList'] = [p for p in self.categoria['m_ChildObjectList']
                                               if p['m_Id'] not in fuera]
        g['m_Edges'] = [e for e in g['m_Edges']
                        if e['m_InputSlot']['m_Node']['m_Id'] not in fuera
                        and e['m_OutputSlot']['m_Node']['m_Id'] not in fuera]
        self.mult_tex = None

    def alpha_clip(self, umbral=0.5):
        """Activa Alpha Clip y añade el bloque Alpha Clip Threshold (no viene en la plantilla).
        Devuelve el bloque Alpha para conectarle el valor."""
        self.target['m_AlphaClip'] = True
        alpha = next(o for o in self.objs if o.get('m_Name') == 'SurfaceDescription.Alpha')
        clip_block = copy.deepcopy(alpha)
        clip_slot = {'m_SGVersion': 0, 'm_Type': SLOT + 'Vector1MaterialSlot',
                     'm_ObjectId': nid(), 'm_Id': 0, 'm_DisplayName': 'Alpha Clip Threshold',
                     'm_SlotType': 0, 'm_Hidden': False, 'm_ShaderOutputName': 'AlphaClipThreshold',
                     'm_StageCapability': 2, 'm_Value': float(umbral), 'm_DefaultValue': 0.5,
                     'm_Labels': []}
        clip_block.update({'m_ObjectId': nid(), 'm_Name': 'SurfaceDescription.AlphaClipThreshold',
                           'm_SerializedDescriptor': 'SurfaceDescription.AlphaClipThreshold',
                           'm_Slots': [{'m_Id': clip_slot['m_ObjectId']}]})
        self.nuevos += [clip_block, clip_slot]
        self.g['m_Nodes'].append({'m_Id': clip_block['m_ObjectId']})
        self.g['m_FragmentContext']['m_Blocks'].append({'m_Id': clip_block['m_ObjectId']})
        return alpha

    # ---------------------------------------------------------------- nodos
    def nodo(self, tipo, x, y, extra=None, valores=None, grupo=''):
        _, tpl, slots = self.T[tipo]
        n = copy.deepcopy(tpl)
        n['m_ObjectId'] = nid()
        n['m_Group'] = {'m_Id': grupo}
        self.pos(n, x, y)
        n['m_DrawState']['m_Position']['width'] = 0.0
        n['m_DrawState']['m_Position']['height'] = 0.0
        n['m_PreviewExpanded'] = True
        n['m_Slots'] = []
        for s in slots:
            s = copy.deepcopy(s)
            s['m_ObjectId'] = nid()
            if valores and s['m_Id'] in valores:
                s['m_Value'] = valores[s['m_Id']]
            n['m_Slots'].append({'m_Id': s['m_ObjectId']})
            self.nuevos.append(s)
        if extra:
            n.update(extra)
        self.nuevos.append(n)
        self.g['m_Nodes'].append({'m_Id': n['m_ObjectId']})
        return n

    def arista(self, a, sa, b, sb):
        self.g['m_Edges'].append({
            'm_OutputSlot': {'m_Node': {'m_Id': a['m_ObjectId']}, 'm_SlotId': sa},
            'm_InputSlot': {'m_Node': {'m_Id': b['m_ObjectId']}, 'm_SlotId': sb}})

    def _registrar_prop(self, p):
        self.nuevos.append(p)
        self.g['m_Properties'].append({'m_Id': p['m_ObjectId']})
        self.categoria['m_ChildObjectList'].append({'m_Id': p['m_ObjectId']})
        return p

    def prop_float(self, nombre, ref, valor, lo=None, hi=None):
        p = copy.deepcopy(self.T['Vector1ShaderProperty'][1])
        p.update({'m_ObjectId': nid(), 'm_Guid': {'m_GuidSerialized': str(uuid.uuid4())},
                  'm_Name': nombre, 'm_RefNameGeneratedByDisplayName': nombre,
                  'm_DefaultReferenceName': '_' + nombre.replace(' ', '_'),
                  'm_OverrideReferenceName': ref, 'm_Value': float(valor)})
        for k, v in (('m_DismissedVersion', 0), ('m_Precision', 0),
                     ('m_PerRendererData', False), ('m_customAttributes', [])):
            p.setdefault(k, v)
        if lo is None:
            p['m_FloatType'], p['m_RangeValues'] = 0, v2(0, 1)
        else:
            p['m_FloatType'], p['m_RangeValues'] = 1, v2(lo, hi)
        return self._registrar_prop(p)

    def prop_color_nueva(self, nombre, ref, rgba, hdr=False):
        p = copy.deepcopy(self.prop_color)
        p.update({'m_ObjectId': nid(), 'm_Guid': {'m_GuidSerialized': str(uuid.uuid4())},
                  'm_Name': nombre, 'm_RefNameGeneratedByDisplayName': nombre,
                  'm_DefaultReferenceName': '_' + nombre.replace(' ', '_'),
                  'm_OverrideReferenceName': ref, 'm_ColorMode': 1 if hdr else 0,
                  'm_Value': dict(zip('rgba', map(float, rgba)))})
        return self._registrar_prop(p)

    def prop_nodo(self, prop, x, y, grupo=''):
        _, tpl, slots = self.T['PropertyNode']
        n = copy.deepcopy(tpl)
        n['m_ObjectId'] = nid()
        n['m_Group'] = {'m_Id': grupo}
        self.pos(n, x, y)
        n['m_Property'] = {'m_Id': prop['m_ObjectId']}
        s = copy.deepcopy(slots[0])
        s['m_ObjectId'] = nid()
        s['m_DisplayName'] = prop['m_Name']
        if prop['m_Type'].endswith('ColorShaderProperty'):
            s['m_Type'] = SLOT + 'Vector4MaterialSlot'
            s['m_Value'] = s['m_DefaultValue'] = v4(0)
        n['m_Slots'] = [{'m_Id': s['m_ObjectId']}]
        self.nuevos += [s, n]
        self.g['m_Nodes'].append({'m_Id': n['m_ObjectId']})
        return n

    def funcion(self, nombre, cuerpo, entradas, salidas, x, y, grupo=''):
        """Custom Function inline (tipo String). entradas/salidas: [(nombre, 'float'|'float3')]."""
        _, tpl, _ = self.T['CustomFunctionNode']
        n = copy.deepcopy(tpl)
        n.update({'m_ObjectId': nid(), 'm_Group': {'m_Id': grupo}, 'm_Name': nombre,
                  'm_SourceType': 1, 'm_FunctionName': nombre, 'm_FunctionSource': '',
                  'm_FunctionBody': cuerpo, 'm_PreviewExpanded': False})
        self.pos(n, x, y)
        n['m_Slots'] = []
        for i, (nom, tipo) in enumerate(list(entradas) + list(salidas)):
            es_salida = i >= len(entradas)
            if tipo == 'float3':
                s = copy.deepcopy(self.T['Vector3MaterialSlot'][1])
                s['m_Value'] = s['m_DefaultValue'] = {'x': 0.0, 'y': 0.0, 'z': 0.0}
            else:
                s = copy.deepcopy(self.T['Vector1MaterialSlot'][1])
                s['m_Value'] = s['m_DefaultValue'] = 0.0
            s.update({'m_ObjectId': nid(), 'm_Id': i, 'm_DisplayName': nom,
                      'm_ShaderOutputName': nom, 'm_SlotType': 1 if es_salida else 0,
                      'm_StageCapability': 3, 'm_Labels': []})
            n['m_Slots'].append({'m_Id': s['m_ObjectId']})
            self.nuevos.append(s)
        self.nuevos.append(n)
        self.g['m_Nodes'].append({'m_Id': n['m_ObjectId']})
        return n

    def grupo(self, titulo, x, y):
        gd = {'m_SGVersion': 0, 'm_Type': SLOT + 'GroupData', 'm_ObjectId': nid(),
              'm_Title': titulo, 'm_Position': v2(x, y)}
        self.nuevos.append(gd)
        self.g['m_GroupDatas'].append({'m_Id': gd['m_ObjectId']})
        return gd['m_ObjectId']

    def nota(self, texto, x, y, w=420, h=100, grupo=''):
        s = {'m_SGVersion': 0, 'm_Type': SLOT + 'StickyNoteData', 'm_ObjectId': nid(),
             'm_Title': '', 'm_Content': texto, 'm_TextSize': 0, 'm_Theme': 0,
             'm_Position': {'serializedVersion': '2', 'x': float(x), 'y': float(y),
                            'width': float(w), 'height': float(h)},
             'm_Group': {'m_Id': grupo}}
        self.nuevos.append(s)
        self.g['m_StickyNoteDatas'].append({'m_Id': s['m_ObjectId']})

    # --------------------------------------------------------------- guardar
    def guardar(self, ruta):
        todo = self.objs + self.nuevos
        with open(ruta, 'w', encoding='utf-8') as f:
            f.write('\n\n'.join(json.dumps(o, indent=4) for o in todo) + '\n\n')
        ids = {o['m_ObjectId']: o for o in todo}

        def refs(x):
            if isinstance(x, dict):
                if set(x) == {'m_Id'} and isinstance(x['m_Id'], str) and x['m_Id']:
                    yield x['m_Id']
                for v in x.values():
                    yield from refs(v)
            elif isinstance(x, list):
                for v in x:
                    yield from refs(v)
        rotas = [r for o in todo for r in refs(o) if r not in ids]
        malas = 0
        for e in self.g['m_Edges']:
            for lado, quiere in (('m_OutputSlot', 1), ('m_InputSlot', 0)):
                nodo = ids[e[lado]['m_Node']['m_Id']]
                if not any(ids[s['m_Id']]['m_Id'] == e[lado]['m_SlotId']
                           and ids[s['m_Id']]['m_SlotType'] == quiere for s in nodo['m_Slots']):
                    malas += 1
                    print('ARISTA MALA', nodo.get('m_Name'), lado, e[lado]['m_SlotId'])
        # cada entrada solo puede tener una conexión
        entradas = [(e['m_InputSlot']['m_Node']['m_Id'], e['m_InputSlot']['m_SlotId'])
                    for e in self.g['m_Edges']]
        dup = len(entradas) - len(set(entradas))
        print(f'{os.path.basename(ruta)}: objetos={len(todo)} referencias rotas={rotas} '
              f'aristas malas={malas} entradas duplicadas={dup}')
