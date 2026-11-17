#!/usr/bin/env python3
"""Genera Assets/Shaders/BordesBorderlands.shadergraph: efecto de pantalla completa (URP Fullscreen)
que dibuja líneas de tinta estilo Borderlands detectando bordes en profundidad y normales.
El color y la activación vienen de cada material (Color Bordes) vía MascaraBordesFeature.
Se usa con un Full Screen Pass Renderer Feature en el renderer de URP."""
import os
import copy
import sys
from sg_comun import Grafo, PROYECTO, PLANTILLA, cargar, nid, v4, SLOT

G = Grafo('Proyecto Final', pantalla=True)
fs = next(o for o in G.objs if o['m_Type'].endswith('FullscreenData'))
fs.update({'m_BlendMode': 1, 'm_EnableStencil': False})   # Alpha: líneas de cualquier color
N, A, P = G.nodo, G.arista, G.prop_nodo

# ------------------------------------------------------------------ propiedades
p_grosor = G.prop_float('Grosor', '_Grosor', 3, 0.5, 8)
p_ginter = G.prop_float('Grosor Interior', '_GrosorInterior', 0.5, 0, 1)
p_aten = G.prop_float('Atenuacion Distancia', '_AtenuacionDistancia', 0.04, 0, 0.3)
p_var = G.prop_float('Variacion Trazo', '_VariacionTrazo', 0.4, 0, 1)
p_evar = G.prop_float('Escala Variacion', '_EscalaVariacion', 40, 1, 200)
p_uprof = G.prop_float('Umbral Profundidad', '_UmbralProfundidad', 0.08, 0.005, 0.5)
p_unor = G.prop_float('Umbral Normales', '_UmbralNormales', 0.3, 0.01, 1)
p_iint = G.prop_float('Intensidad Interior', '_IntensidadInterior', 1, 0, 1)
p_opac = G.prop_float('Opacidad', '_Opacidad', 1, 0, 1)
p_dur = G.prop_float('Dureza', '_Dureza', 20, 1, 50)   # 1 = borde suave, alto = línea sólida


def buffer_normales(x, y, grupo):
    """URP Sample Buffer en modo NormalWorldSpace (salida Vector3)."""
    n = N('UniversalSampleBufferNode', x, y, extra={'m_BufferType': 0}, grupo=grupo)
    salida = next(o for o in G.nuevos if o['m_ObjectId'] == n['m_Slots'][1]['m_Id'])
    salida['m_Type'] = SLOT + 'Vector3MaterialSlot'
    salida['m_Value'] = salida['m_DefaultValue'] = {'x': 0.0, 'y': 0.0, 'z': 0.0}
    salida.pop('m_ColorMode', None)
    return n


def profundidad(x, y, grupo):
    return N('SceneDepthNode', x, y, extra={'m_DepthSamplingMode': 2}, grupo=grupo)   # Eye (metros)


# ================= 1) Coordenadas y profundidad del píxel ======================
g1 = G.grupo('1) Píxel actual', -2400, -200)
sp = N('ScreenPositionNode', -2350, -100, grupo=g1)
uv = N('SwizzleNode', -2150, -100, grupo=g1)                                   # xy
dC = profundidad(-1950, -100, g1)
scr = N('ScreenNode', -2350, 60, grupo=g1)
inv_w = N('DivideNode', -2150, 40, valores={0: v4(1)}, grupo=g1)               # 1 / ancho
inv_h = N('DivideNode', -2150, 160, valores={0: v4(1)}, grupo=g1)              # 1 / alto
texel = N('CombineNode', -1950, 80, grupo=g1)                                  # tamaño de 1 píxel en UV
A(sp, 0, uv, 0)
A(uv, 1, dC, 0)
A(scr, 0, inv_w, 1)
A(scr, 1, inv_h, 1)
A(inv_w, 2, texel, 0)
A(inv_h, 2, texel, 1)

# ================= 2) Grosor del trazo ========================================
g2 = G.grupo('2) Grosor: distancia + variación de trazo', -2400, 350)
p_evar_n = P(p_evar, -2350, 560, grupo=g2)
ruido = N('GradientNoiseNode', -2150, 450, grupo=g2)
s_r = N('SubtractNode', -1950, 450, valores={1: v4(0.5)}, grupo=g2)
p_var_n = P(p_var, -1950, 600, grupo=g2)
m_r = N('MultiplyNode', -1750, 450, grupo=g2)
m_r2 = N('MultiplyNode', -1550, 450, valores={1: {**{f'e{i}{j}': 0.0 for i in range(4) for j in range(4)},
                                               'e00': 2.0, 'e01': 2.0, 'e02': 2.0, 'e03': 2.0}}, grupo=g2)
fac = N('AddNode', -1350, 450, valores={1: v4(1)}, grupo=g2)                  # 1 ± variación
p_aten_n = P(p_aten, -1950, 760, grupo=g2)
m_d = N('MultiplyNode', -1750, 720, grupo=g2)
a_d = N('AddNode', -1550, 720, valores={1: v4(1)}, grupo=g2)                  # 1 + dist·aten
p_gr_n = P(p_grosor, -1550, 880, grupo=g2)
d_g = N('DivideNode', -1350, 720, grupo=g2)                                   # grosor / (1 + d·aten)
m_g = N('MultiplyNode', -1150, 600, grupo=g2)
g_px = N('MaximumNode', -950, 600, valores={1: v4(1)}, grupo=g2)              # mínimo 1 píxel
paso = N('MultiplyNode', -750, 300, grupo=g2)                                  # paso de silueta (UV)
p_gi_n = P(p_ginter, -750, 500, grupo=g2)
paso_i = N('MultiplyNode', -550, 400, grupo=g2)                                # paso interior (UV)
A(uv, 1, ruido, 0)
A(p_evar_n, 0, ruido, 1)
A(ruido, 2, s_r, 0)
A(s_r, 2, m_r, 0)
A(p_var_n, 0, m_r, 1)
A(m_r, 2, m_r2, 0)
A(m_r2, 2, fac, 0)
A(dC, 1, m_d, 0)
A(p_aten_n, 0, m_d, 1)
A(m_d, 2, a_d, 0)
A(p_gr_n, 0, d_g, 0)
A(a_d, 2, d_g, 1)
A(d_g, 2, m_g, 0)
A(fac, 2, m_g, 1)
A(m_g, 2, g_px, 0)
A(texel, 6, paso, 0)
A(g_px, 2, paso, 1)
A(paso, 2, paso_i, 0)
A(p_gi_n, 0, paso_i, 1)
G.nota('Borderlands: líneas gruesas de cerca y más finas a lo lejos (Atenuación Distancia), '
       'con grosor irregular como trazo a mano (ruido → Variación Trazo). Las líneas interiores '
       'usan una fracción del grosor (Grosor Interior).', -2350, 960, 460, 100, g2)


def cruz(paso_nodo, x, y, grupo):
    """4 UVs vecinas: uv ± (paso.x, 0), uv ± (0, paso.y)."""
    sp_ = N('SplitNode', x, y, grupo=grupo)
    ox = N('CombineNode', x + 200, y - 60, grupo=grupo)
    oy = N('CombineNode', x + 200, y + 100, grupo=grupo)
    A(paso_nodo, 2, sp_, 0)
    A(sp_, 1, ox, 0)
    A(sp_, 2, oy, 1)
    uvs = []
    for i, (tipo, off) in enumerate((('AddNode', ox), ('SubtractNode', ox), ('AddNode', oy), ('SubtractNode', oy))):
        n = N(tipo, x + 420, y - 120 + i * 110, grupo=grupo)
        A(uv, 1, n, 0)
        A(off, 6, n, 1)
        uvs.append(n)
    return uvs


def max_cadena(nodos_slots, x, y, grupo):
    acc = nodos_slots[0]
    for i, ns in enumerate(nodos_slots[1:]):
        m = N('MaximumNode', x + i * 180, y, grupo=grupo)
        A(acc[0], acc[1], m, 0)
        A(ns[0], ns[1], m, 1)
        acc = (m, 2)
    return acc


def umbral(valor, prop, x, y, grupo):
    """saturate((valor - umbral) / umbral): 0 bajo el umbral, 1 al doble."""
    pn = P(prop, x, y + 120, grupo=grupo)
    s = N('SubtractNode', x + 200, y, grupo=grupo)
    d = N('DivideNode', x + 400, y, grupo=grupo)
    t = N('SaturateNode', x + 600, y, grupo=grupo)
    A(valor[0], valor[1], s, 0)
    A(pn, 0, s, 1)
    A(s, 2, d, 0)
    A(pn, 0, d, 1)
    A(d, 2, t, 0)
    return t


# ================= 3) Silueta: saltos de profundidad ==========================
g3 = G.grupo('3) Silueta (saltos de profundidad)', -300, -500)
uvs_d = cruz(paso, -250, -300, g3)
difs = []
for i, u in enumerate(uvs_d):
    d = profundidad(300, -420 + i * 110, g3)
    s = N('SubtractNode', 500, -420 + i * 110, grupo=g3)
    ab = N('MaximumNode', 700, -420 + i * 110, valores={1: v4(0)}, grupo=g3)   # solo vecinos más lejanos
    A(u, 2, d, 0)
    A(d, 1, s, 0)
    A(dC, 1, s, 1)
    A(s, 2, ab, 0)
    difs.append((ab, 2))
dmax = max_cadena(difs, 900, -300, g3)
dC_seg = N('MaximumNode', 1250, -150, valores={1: v4(0.0001)}, grupo=g3)     # evita dividir entre 0
rel = N('DivideNode', 1450, -300, grupo=g3)                                   # salto relativo
A(dC, 1, dC_seg, 0)
A(dmax[0], dmax[1], rel, 0)
A(dC_seg, 2, rel, 1)
m_sil = umbral((rel, 2), p_uprof, 1650, -300, g3)
G.nota('Compara la profundidad del píxel con 4 vecinos. Si algún vecino está mucho más lejos '
       '(salto relativo a la distancia), este píxel es borde de silueta.', -250, -620, 420, 80, g3)

# ================= 4) Líneas interiores: cambios de normal ====================
g4 = G.grupo('4) Líneas interiores (cambios de normal)', -300, 300)
nC = buffer_normales(300, 300, g4)
A(uv, 1, nC, 0)
uvs_n = cruz(paso_i, -250, 600, g4)
cambios = []
for i, u in enumerate(uvs_n):
    n = buffer_normales(300, 480 + i * 110, g4)
    dt = N('DotProductNode', 500, 480 + i * 110, grupo=g4)
    om = N('OneMinusNode', 700, 480 + i * 110, grupo=g4)
    A(u, 2, n, 0)
    A(n, 2, dt, 0)
    A(nC, 2, dt, 1)
    A(dt, 2, om, 0)
    cambios.append((om, 1))
nmax = max_cadena(cambios, 900, 600, g4)
m_int0 = umbral(nmax, p_unor, 1450, 600, g4)
cam = N('CameraNode', 1450, 850, grupo=g4)
cielo = N('SubtractNode', 1650, 850, grupo=g4)                                # far - profundidad
cielo_s = N('SaturateNode', 1850, 850, grupo=g4)                              # 0 en el cielo
p_ii_n = P(p_iint, 1850, 1000, grupo=g4)
m_int1 = N('MultiplyNode', 2050, 650, grupo=g4)
m_int = N('MultiplyNode', 2250, 700, grupo=g4)
A(cam, 4, cielo, 0)
A(dC, 1, cielo, 1)
A(cielo, 2, cielo_s, 0)
A(m_int0, 1, m_int1, 0)
A(cielo_s, 1, m_int1, 1)
A(m_int1, 2, m_int, 0)
A(p_ii_n, 0, m_int, 1)
G.nota('1 - N·Nvecino crece cuando la superficie dobla: aristas de cubos, pliegues, cruces entre '
       'objetos. El cielo no tiene normales, por eso se enmascara con (far - profundidad).',
       -250, 1000, 440, 80, g4)

# ================= 5) Componer con la máscara de cada material ====================
# MascaraBordesFeature dibuja cada objeto con el "Color Bordes" de su material en la textura
# global _MascaraBordes. Aquí: color de la línea = máscara.rgb, línea solo donde máscara.a > 0.
plantilla = cargar(PLANTILLA)
pby = {o['m_ObjectId']: o for o in plantilla}
tex_prop = copy.deepcopy(next(o for o in plantilla if o['m_Type'].endswith('Texture2DShaderProperty')))
tex_prop.update({'m_ObjectId': nid(), 'm_Name': 'Mascara Bordes', 'm_RefNameGeneratedByDisplayName': 'Mascara Bordes',
                 'm_DefaultReferenceName': '_Mascara_Bordes', 'm_OverrideReferenceName': '_MascaraBordes',
                 'm_GeneratePropertyBlock': False, 'isMainTexture': False, 'useTilingAndOffset': False,
                 'm_DefaultType': 1})                                          # global, no aparece en el material
tex_prop['m_Guid'] = {'m_GuidSerialized': str(__import__('uuid').uuid4())}
G._registrar_prop(tex_prop)
tpl_nodo = next(o for o in plantilla if o['m_Type'].endswith('.PropertyNode')
                and pby[o['m_Slots'][0]['m_Id']]['m_Type'].endswith('Texture2DMaterialSlot'))
n_tex = copy.deepcopy(tpl_nodo)
s_tex = copy.deepcopy(pby[tpl_nodo['m_Slots'][0]['m_Id']])
s_tex.update({'m_ObjectId': nid(), 'm_DisplayName': 'Mascara Bordes'})
n_tex.update({'m_ObjectId': nid(), 'm_Property': {'m_Id': tex_prop['m_ObjectId']},
              'm_Slots': [{'m_Id': s_tex['m_ObjectId']}], 'm_Group': {'m_Id': ''}})
G.pos(n_tex, 2050, -450)
G.nuevos += [s_tex, n_tex]
G.g['m_Nodes'].append({'m_Id': n_tex['m_ObjectId']})

g5 = G.grupo('5) Color y activación por material (máscara)', 2000, -550)
muestra = N('SampleTexture2DNode', 2300, -450, grupo=g5)
A(n_tex, 0, muestra, 1)
A(uv, 1, muestra, 2)
borde = N('MaximumNode', 2050, -50, grupo=g5)
p_op_n = P(p_opac, 2050, 100, grupo=g5)
borde_o = N('MultiplyNode', 2250, -50, grupo=g5)
borde_m = N('MultiplyNode', 2450, -50, grupo=g5)                              # × alfa de la máscara
borde_s = N('SaturateNode', 2650, -50, grupo=g5)
# dureza: (borde - 0.5) · Dureza + 0.5 → casi binario, la línea queda del color exacto
p_dur_n = P(p_dur, 2050, -250, grupo=g5)
s_med = N('SubtractNode', 2250, -200, valores={1: v4(0.5)}, grupo=g5)
m_dur = N('MultiplyNode', 2450, -200, grupo=g5)
a_med = N('AddNode', 2650, -200, valores={1: v4(0.5)}, grupo=g5)
sat_d = N('SaturateNode', 2850, -200, grupo=g5)
A(m_sil, 1, borde, 0)
A(m_int, 2, borde, 1)
A(borde, 2, s_med, 0)
A(s_med, 2, m_dur, 0)
A(p_dur_n, 0, m_dur, 1)
A(m_dur, 2, a_med, 0)
A(a_med, 2, sat_d, 0)
A(sat_d, 1, borde_o, 0)
A(p_op_n, 0, borde_o, 1)
A(borde_o, 2, borde_m, 0)
A(muestra, 7, borde_m, 1)
A(borde_m, 2, borde_s, 0)
A(muestra, 0, G.base_color, 0)
A(borde_s, 1, G.alpha, 0)
G.nota('Dureza vuelve la línea sólida (sin mezclarse con lo de abajo). Blend Mode = Alpha. Color = color de la máscara (el "Color Bordes" del material del objeto); '
       'alpha = línea × alfa de la máscara. Materiales sin Color Bordes (o con alfa 0) no llevan '
       'líneas. La silueta se dibuja del lado del objeto más cercano para tomar su color.',
       2050, 200, 460, 100, g5)

G.guardar(os.path.join(PROYECTO, 'Assets/Shaders/BordesBorderlands.shadergraph'))
