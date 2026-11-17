#!/usr/bin/env python3
"""Genera Assets/Shaders/DitherVanish.shadergraph (para efectos, desvanecido en la sombra / swoosh):
sombreado halftone (puntos según la luz, en pantalla) + desvanecido por dithering:
el porcentaje 'Desvanecer' (0-100 %) abre agujeros en una rejilla de puntos hasta borrar el objeto.
Opaco con Alpha Clip: no tiene problemas de orden de transparencias."""
import copy
import os
from sg_comun import Grafo, PROYECTO, nid, v2, v4

G = Grafo('Proyecto Final/Efectos')
G.target['m_AlphaClip'] = True
N, A, P = G.nodo, G.arista, G.prop_nodo

# --- bloque Alpha Clip Threshold (no viene en la plantilla) --------------------
alpha_block = next(o for o in G.objs if o.get('m_Name') == 'SurfaceDescription.Alpha')
clip_block = copy.deepcopy(alpha_block)
clip_slot = {'m_SGVersion': 0, 'm_Type': 'UnityEditor.ShaderGraph.Vector1MaterialSlot',
             'm_ObjectId': nid(), 'm_Id': 0, 'm_DisplayName': 'Alpha Clip Threshold',
             'm_SlotType': 0, 'm_Hidden': False, 'm_ShaderOutputName': 'AlphaClipThreshold',
             'm_StageCapability': 2, 'm_Value': 0.0, 'm_DefaultValue': 0.5, 'm_Labels': []}
clip_block.update({'m_ObjectId': nid(), 'm_Name': 'SurfaceDescription.AlphaClipThreshold',
                   'm_SerializedDescriptor': 'SurfaceDescription.AlphaClipThreshold',
                   'm_Slots': [{'m_Id': clip_slot['m_ObjectId']}]})
G.nuevos += [clip_block, clip_slot]
G.g['m_Nodes'].append({'m_Id': clip_block['m_ObjectId']})
G.g['m_FragmentContext']['m_Blocks'].append({'m_Id': clip_block['m_ObjectId']})

# ------------------------------------------------------------------ propiedades
p_tinta = G.prop_color_nueva('Color Tinta', '_ColorTinta', (0.05, 0.03, 0.08, 1))
# Líneas Borderlands de este material (las lee MascaraBordesFeature). Alfa 0 = sin líneas.
p_bordes = G.prop_color_nueva('Color Bordes', '_ColorBordes', (0.02, 0.015, 0.03, 0))
p_dens = G.prop_float('Densidad de Puntos', '_DensidadPuntos', 70, 5, 200)
p_ang = G.prop_float('Angulo', '_Angulo', 45, 0, 90)
p_int = G.prop_float('Intensidad Sombra', '_IntensidadSombra', 0.85, 0, 1.5)
p_suav = G.prop_float('Suavizado', '_Suavizado', 0.08, 0.001, 0.5)
p_desv = G.prop_float('Desvanecer', '_Desvanecer', 0, 0, 100)                  # porcentaje
p_ddens = G.prop_float('Densidad Desvanecer', '_DensidadDesvanecer', 90, 5, 300)
p_angl = G.prop_float('Angulo Luz', '_AnguloLuz', 90, 0, 180)                  # grados desde la luz
p_anch = G.prop_float('Ancho Transicion', '_AnchoTransicion', 0.3, 0.01, 1)
p_cborde = G.prop_color_nueva('Color Borde Desvanecer', '_ColorBordeDesvanecer', (0.3, 2.0, 3.0, 1), hdr=True)
p_aborde = G.prop_float('Ancho Borde Desvanecer', '_AnchoBordeDesvanecer', 0.06, 0, 0.3)
# cuánto después de la sombra se empieza a borrar la luz (0 = todos los agujeros iguales)
p_retr = G.prop_float('Retraso Luz', '_RetrasoLuz', 1.5, 0, 4)


def rejilla(x, y, grupo, prop_densidad):
    """Distancia de cada píxel al centro de su celda (rejilla rotada en pantalla)."""
    sp = N('ScreenPositionNode', x, y, grupo=grupo)
    sw = N('SwizzleNode', x + 220, y, grupo=grupo)
    scr = N('ScreenNode', x, y + 160, grupo=grupo)
    asp = N('DivideNode', x + 220, y + 160, grupo=grupo)
    comb = N('CombineNode', x + 420, y + 160, valores={1: 1.0}, grupo=grupo)
    m_a = N('MultiplyNode', x + 640, y, grupo=grupo)
    ang = P(p_ang, x + 640, y + 220, grupo=grupo)
    rot = N('RotateNode', x + 860, y, extra={'m_Unit': 1}, valores={1: v2(0, 0)}, grupo=grupo)
    dens = P(prop_densidad, x + 860, y + 220, grupo=grupo)
    m_d = N('MultiplyNode', x + 1080, y, grupo=grupo)
    fr = N('FractionNode', x + 1280, y, grupo=grupo)
    sb = N('SubtractNode', x + 1480, y, valores={1: v4(0.5)}, grupo=grupo)
    ln = N('LengthNode', x + 1680, y, grupo=grupo)
    A(sp, 0, sw, 0)
    A(scr, 0, asp, 0)
    A(scr, 1, asp, 1)
    A(asp, 2, comb, 0)
    A(sw, 1, m_a, 0)
    A(comb, 6, m_a, 1)
    A(m_a, 2, rot, 0)
    A(ang, 0, rot, 2)
    A(rot, 3, m_d, 0)
    A(dens, 0, m_d, 1)
    A(m_d, 2, fr, 0)
    A(fr, 1, sb, 0)
    A(sb, 2, ln, 0)
    return ln


# ================= 1) Sombreado halftone ======================================
g1 = G.grupo('1) Sombreado con puntos (luz principal)', -3000, -500)
dist = rejilla(-2950, -400, g1, p_dens)
normal = N('NormalVectorNode', -2950, -100, grupo=g1)
luz = N('MainLightDirectionNode', -2950, 30, grupo=g1)
dot = N('DotProductNode', -2730, -60, grupo=g1)
remap = N('RemapNode', -2510, -60, valores={1: v2(-1, 1), 2: v2(0, 1)}, grupo=g1)   # dot = -N·L: luz → 0, sombra → 1
p_int_n = P(p_int, -2510, 120, grupo=g1)
radio = N('MultiplyNode', -2290, -60, grupo=g1)
s_r = N('SubtractNode', -1150, -300, grupo=g1)
p_suav_n = P(p_suav, -1150, -120, grupo=g1)
d_s = N('DivideNode', -950, -300, grupo=g1)
papel = N('SaturateNode', -750, -300, grupo=g1)                                # 1 = papel, 0 = tinta
A(normal, 0, dot, 0)
A(luz, 0, dot, 1)
A(dot, 2, remap, 0)
A(remap, 3, radio, 0)
A(p_int_n, 0, radio, 1)
A(dist, 1, s_r, 0)
A(radio, 2, s_r, 1)
A(s_r, 2, d_s, 0)
A(p_suav_n, 0, d_s, 1)
A(d_s, 2, papel, 0)

# ================= 2) Desvanecer por dithering =================================
g2 = G.grupo('2) Desvanecer (dithering + alpha clip)', -3000, 500)
dist_v = rejilla(-2950, 600, g2, p_ddens)
p_desv_n = P(p_desv, -1150, 820, grupo=g2)
pct = N('DivideNode', -950, 820, valores={1: v4(100)}, grupo=g2)               # % → 0..1
A(p_desv_n, 0, pct, 0)

# ¿qué tan en sombra está el píxel respecto al "Angulo Luz"?
MENOS1 = {**{f'e{i}{j}': 0.0 for i in range(4) for j in range(4)}, 'e00': -1.0, 'e01': -1.0, 'e02': -1.0, 'e03': -1.0}
GRAD = {**{f'e{i}{j}': 0.0 for i in range(4) for j in range(4)}, 'e00': 0.0174533, 'e01': 0.0174533, 'e02': 0.0174533, 'e03': 0.0174533}
ndl = N('MultiplyNode', -2300, 1150, valores={1: MENOS1}, grupo=g2)           # N·L (1 = de frente a la luz)
p_angl_n = P(p_angl, -2300, 1320, grupo=g2)
rad = N('MultiplyNode', -2100, 1320, valores={1: GRAD}, grupo=g2)              # grados → radianes
cosA = N('CosineNode', -1900, 1320, grupo=g2)
dif = N('SubtractNode', -1700, 1200, grupo=g2)                                 # cos(ángulo) - N·L
p_anch_n = P(p_anch, -1700, 1380, grupo=g2)
d_an = N('DivideNode', -1500, 1200, grupo=g2)
sombra = N('SaturateNode', -1300, 1200, grupo=g2)                              # 0 = luz, 1 = sombra
A(dot, 2, ndl, 0)
A(p_angl_n, 0, rad, 0)
A(rad, 2, cosA, 0)
uno_a = N('AddNode', -1900, 1450, valores={1: v4(1)}, grupo=g2)              # 1 + ancho
cos_e = N('MultiplyNode', -1700, 1350, grupo=g2)                               # umbral extendido
A(cosA, 1, cos_e, 0)
A(uno_a, 2, cos_e, 1)
A(cos_e, 2, dif, 0)
A(ndl, 2, dif, 1)
A(dif, 2, d_an, 0)
A(p_anch_n, 0, d_an, 1)
A(d_an, 2, sombra, 0)
A(p_anch_n, 0, uno_a, 0)
# luz continua 0..1: N·L, y 0 en lo que Angulo Luz marca como sombra (swoosh)
luz_s = N('SaturateNode', -1300, 1050, grupo=g2)                               # max(N·L, 0)
om_s = N('OneMinusNode', -1150, 1200, grupo=g2)
luz = N('MultiplyNode', -1150, 1050, grupo=g2)                                 # 0 sombra .. 1 luz
A(ndl, 2, luz_s, 0)
A(sombra, 1, om_s, 0)
A(luz_s, 1, luz, 0)
A(om_s, 1, luz, 1)
# cantidad = saturate(pct·(1+R) − luz·R): con más luz el agujero empieza más tarde y es más chico
p_retr_n = P(p_retr, -1150, 900, grupo=g2)
uno_r = N('AddNode', -950, 950, valores={1: v4(1)}, grupo=g2)                  # 1 + R
m_pr = N('MultiplyNode', -800, 1000, grupo=g2)                                 # pct·(1+R)
m_lr = N('MultiplyNode', -950, 1100, grupo=g2)                                 # luz·R
sub_l = N('SubtractNode', -650, 1050, grupo=g2)
cant = N('SaturateNode', -850, 900, grupo=g2)                                  # 0..1 a borrar
A(p_retr_n, 0, uno_r, 0)
A(pct, 2, m_pr, 0)
A(uno_r, 2, m_pr, 1)
A(luz, 2, m_lr, 0)
A(p_retr_n, 0, m_lr, 1)
A(m_pr, 2, sub_l, 0)
A(m_lr, 2, sub_l, 1)
A(sub_l, 2, cant, 0)

# radio máximo 0.75 > 0.717 (esquina de la celda + 0.01): a 100 % no quedan puntitos
r_v = N('MultiplyNode', -750, 820, valores={1: {**{f'e{i}{j}': 0.0 for i in range(4) for j in range(4)},
                                                'e00': 0.75, 'e01': 0.75, 'e02': 0.75, 'e03': 0.75}}, grupo=g2)
d_e = N('AddNode', -1050, 600, valores={1: v4(0.01)}, grupo=g2)                # distancia + 0.01
alfa = N('SubtractNode', -550, 650, grupo=g2)                                  # < 0 → se recorta
A(cant, 1, r_v, 0)
A(dist_v, 1, d_e, 0)
A(d_e, 2, alfa, 0)
A(r_v, 2, alfa, 1)
A(alfa, 2, alpha_block, 0)
G.nota('Swoosh: un píxel es "luz" si el ángulo entre su normal y la luz es menor que Angulo Luz '
       '(N·L > cos(ángulo)·(1+ancho), así 0° todo es sombra y 180° todo es luz). Luz = N·L fuera de esa '
       'sombra (0 dentro). Con la sombra ya borrada (100/(1+Retraso Luz) %), anima Angulo Luz de 180 '
       'a 0 y la parte visible se encoge hacia el lado iluminado (swoosh).', -2300, 1480, 480, 110, g2)
G.nota('Cada celda abre un agujero con radio = saturate(Desvanecer·(1+R) − luz·R) × 0.75 (R = Retraso '
       'Luz): en la sombra los agujeros nacen antes y son más grandes, en la luz son más chicos y '
       'llegan al final. Alpha = distancia - radio; Alpha Clip Threshold = 0 descarta alpha < 0. '
       '0 % = completo, 100 % = desaparece todo.',
       -2950, 900, 460, 110, g2)

# borde brillante alrededor de los agujeros (para efectos)
p_ab_n = P(p_aborde, -550, 850, grupo=g2)
d_b = N('DivideNode', -350, 650, grupo=g2)                                     # alpha / ancho
sat_b = N('SaturateNode', -150, 650, grupo=g2)
om_b = N('OneMinusNode', 50, 650, grupo=g2)                                    # 1 junto al agujero
gate = N('MultiplyNode', -350, 850, valores={1: {**{f'e{i}{j}': 0.0 for i in range(4) for j in range(4)},
                                                 'e00': 1000.0, 'e01': 1000.0, 'e02': 1000.0, 'e03': 1000.0}}, grupo=g2)
gate_s = N('SaturateNode', -150, 850, grupo=g2)                                # 0 si Desvanecer = 0
borde = N('MultiplyNode', 250, 700, grupo=g2)
A(alfa, 2, d_b, 0)
A(p_ab_n, 0, d_b, 1)
A(d_b, 2, sat_b, 0)
A(sat_b, 1, om_b, 0)
A(pct, 2, gate, 0)
A(gate, 2, gate_s, 0)
A(om_b, 1, borde, 0)
A(gate_s, 1, borde, 1)
G.nota('Borde: los píxeles a menos de "Ancho Borde" del agujero se pintan con Color Borde '
       'Desvanecer (HDR: brilla con Bloom). Se apaga solo cuando Desvanecer = 0.',
       -550, 980, 420, 80, g2)

# ================= 3) Color final ==============================================
g3 = G.grupo('3) Color final', 300, -100)
for o in G.nodos_plantilla('SampleTexture2DNode'):
    G.pos(o, 350, 50)
G.pos(G.nodo_prop_plantilla(G.prop_tex), 350, -30)
G.pos(G.nodo_prop_plantilla(G.prop_color), 600, 250)
G.pos(G.mult_tex, 600, 50)
p_tin_n = P(p_tinta, 820, -60, grupo=g3)
l_tin = N('LerpNode', 1020, 0, grupo=g3)
p_cb_n = P(p_cborde, 1020, 250, grupo=g3)
l_bor = N('LerpNode', 1240, 100, grupo=g3)
A(p_tin_n, 0, l_tin, 0)
A(G.mult_tex, 2, l_tin, 1)
A(papel, 1, l_tin, 2)
A(l_tin, 3, l_bor, 0)
A(p_cb_n, 0, l_bor, 1)
A(borde, 2, l_bor, 2)
A(l_bor, 3, G.base_color, 0)

G.guardar(os.path.join(PROYECTO, 'Assets/Shaders/DitherVanish.shadergraph'))
