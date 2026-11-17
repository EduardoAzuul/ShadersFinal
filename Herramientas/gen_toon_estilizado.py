#!/usr/bin/env python3
"""Genera Assets/Shaders/ToonComicEstilizado.shadergraph:
toon por bandas + sombras proyectadas + puntos halftone pegados al objeto (zona clara limpia)
+ brillo especular duro + luz de borde."""
import os
from sg_comun import Grafo, PROYECTO, v2, v4

G = Grafo('Proyecto Final')
G.subtarget['m_KeepLightingVariants'] = True   # trae keywords de sombras + Lighting.hlsl

N, A, P = G.nodo, G.arista, G.prop_nodo

# ------------------------------------------------------------------ propiedades
p_sombra = G.prop_color_nueva('Color Sombra', '_ColorSombra', (0.45, 0.4, 0.6, 1))
# Líneas Borderlands de este material (las lee MascaraBordesFeature). Alfa 0 = sin líneas.
p_bordes = G.prop_color_nueva('Color Bordes', '_ColorBordes', (0.02, 0.015, 0.03, 1))
p_bandas = G.prop_float('Bandas', '_Bandas', 3, 2, 6)
p_fsombra = G.prop_float('Fuerza Sombra Proyectada', '_FuerzaSombra', 1, 0, 1)
p_tinta = G.prop_color_nueva('Color Tinta', '_ColorTinta', (0.05, 0.03, 0.08, 1))
p_escala = G.prop_float('Densidad de Puntos', '_EscalaTrama', 25, 1, 150)
p_nit = G.prop_float('Nitidez Triplanar', '_NitidezTriplanar', 8, 1, 32)
p_ang = G.prop_float('Angulo', '_Angulo', 45, 0, 90)
p_int = G.prop_float('Intensidad Tinta', '_IntensidadTinta', 1.2, 0, 2)
p_upun = G.prop_float('Umbral Puntos', '_UmbralPuntos', 0.35, 0, 1)
p_limp = G.prop_float('Limpiar Zona Clara', '_LimpiarZonaClara', 1, 0, 1)
p_suav = G.prop_float('Suavizado', '_Suavizado', 0.08, 0.001, 0.5)
p_cbri = G.prop_color_nueva('Color Brillo', '_ColorBrillo', (1, 1, 1, 1))
p_bri = G.prop_float('Brillo', '_Brillo', 60, 1, 256)
p_fbri = G.prop_float('Fuerza Brillo', '_FuerzaBrillo', 1, 0, 1)
p_cbor = G.prop_color_nueva('Color Borde', '_ColorBorde', (1, 0.93, 0.75, 1))
p_abor = G.prop_float('Ancho Borde', '_AnchoBorde', 0.3, 0, 1)

# ================= 1) Luz principal con sombras ===============================
g1 = G.grupo('1) Luz principal + sombras proyectadas', -3600, -200)
pos_ws = N('PositionNode', -3550, -100, extra={'m_Space': 2}, grupo=g1)        # mundo
luz = G.funcion('LuzPrincipal', r'''#ifdef SHADERGRAPH_PREVIEW
    Direccion = normalize(float3(0.5, 0.7, -0.5));
    ColorLuz = float3(1, 1, 1);
    Sombra = 1;
#else
    #if defined(UNIVERSAL_LIGHTING_INCLUDED)
        // coordenada en el shadow map de la luz principal
        float4 coordSombra = TransformWorldToShadowCoord(PosicionWS);
        Light luz = GetMainLight(coordSombra);
        Direccion = luz.direction;          // apunta HACIA la luz
        ColorLuz = luz.color;
        Sombra = luz.shadowAttenuation;     // 0 = en sombra, 1 = iluminado
    #else
        Direccion = normalize(float3(0.5, 0.7, -0.5));
        ColorLuz = float3(1, 1, 1);
        Sombra = 1;
    #endif
#endif''', [('PosicionWS', 'float3')],
    [('Direccion', 'float3'), ('ColorLuz', 'float3'), ('Sombra', 'float')], -3300, -100, g1)
A(pos_ws, 0, luz, 0)
G.nota('Custom Function: pide a URP la luz principal y su sombra (shadow map). '
       'Para que compile con sombras, el Unlit tiene activado "Keep Lighting Variants" '
       'en Graph Settings.', -3550, 80, 420, 90, g1)

# ================= 2) Luz toon ================================================
g2 = G.grupo('2) Luz toon (bandas)', -3600, 300)
normal = N('NormalVectorNode', -3550, 400, grupo=g2)                           # mundo
dot_nl = N('DotProductNode', -3300, 400, grupo=g2)
mul05 = N('MultiplyNode', -3080, 400, valores={1: {**{f'e{i}{j}': 0.0 for i in range(4) for j in range(4)}, 'e00': 0.5, 'e01': 0.5, 'e02': 0.5, 'e03': 0.5}}, grupo=g2)
add05 = N('AddNode', -2860, 400, valores={1: v4(0.5)}, grupo=g2)               # Half-Lambert 0..1
p_fs_n = P(p_fsombra, -3080, 620, grupo=g2)
lerp_sh = N('LerpNode', -2860, 560, valores={0: v4(1)}, grupo=g2)              # lerp(1, Sombra, Fuerza)
mul_L = N('MultiplyNode', -2640, 420, grupo=g2)                                # L
one_minus = N('OneMinusNode', -2420, 300, grupo=g2)                            # D = 1 - L
p_band_n = P(p_bandas, -2640, 640, grupo=g2)
mul_b = N('MultiplyNode', -2420, 460, grupo=g2)
floor_n = N('FloorNode', -2200, 460, grupo=g2)
sub_b = N('SubtractNode', -2420, 640, valores={1: v4(1)}, grupo=g2)
div_b = N('DivideNode', -1980, 460, grupo=g2)
banda = N('SaturateNode', -1760, 460, grupo=g2)
A(normal, 0, dot_nl, 0)
A(luz, 1, dot_nl, 1)
A(dot_nl, 2, mul05, 0)
A(mul05, 2, add05, 0)
A(luz, 3, lerp_sh, 1)
A(p_fs_n, 0, lerp_sh, 2)
A(add05, 2, mul_L, 0)
A(lerp_sh, 3, mul_L, 1)
A(mul_L, 2, one_minus, 0)
A(mul_L, 2, mul_b, 0)
A(p_band_n, 0, mul_b, 1)
A(mul_b, 2, floor_n, 0)
A(p_band_n, 0, sub_b, 0)
A(floor_n, 1, div_b, 0)
A(sub_b, 2, div_b, 1)
A(div_b, 2, banda, 0)
G.nota('L = (N·Dir)·0.5 + 0.5 (Half-Lambert), multiplicado por la sombra proyectada. '
       'Bandas: floor(L·Bandas)/(Bandas-1). D = 1 - L controla la tinta.',
       -3550, 760, 420, 80, g2)

# ================= 3) Trama triplanar pegada al objeto =======================
g3 = G.grupo('3) Trama triplanar (espacio objeto)', -3600, 950)
pos_os = N('PositionNode', -3550, 1050, extra={'m_Space': 0}, grupo=g3)        # objeto
obj = N('ObjectNode', -3550, 1180, grupo=g3)
mul_sc = N('MultiplyNode', -3330, 1050, grupo=g3)                              # × escala del objeto
p_esc_n = P(p_escala, -3330, 1250, grupo=g3)
mul_esc = N('MultiplyNode', -3110, 1050, grupo=g3)
p_ang_n = P(p_ang, -3110, 1650, grupo=g3)
A(pos_os, 0, mul_sc, 0)
A(obj, 1, mul_sc, 1)
A(mul_sc, 2, mul_esc, 0)
A(p_esc_n, 0, mul_esc, 1)

# una rejilla de puntos por cada plano de proyección
dists = []
for i, eje in enumerate(('yz', 'xz', 'xy')):
    y = 1050 + i * 200
    sw = N('SwizzleNode', -2890, y, extra={'_maskInput': eje, 'convertedMask': eje}, grupo=g3)
    rot = N('RotateNode', -2670, y, extra={'m_Unit': 1}, valores={1: v2(0, 0)}, grupo=g3)
    frac = N('FractionNode', -2450, y, grupo=g3)
    sub_c = N('SubtractNode', -2230, y, valores={1: v4(0.5)}, grupo=g3)
    ln = N('LengthNode', -2010, y, grupo=g3)
    A(mul_esc, 2, sw, 0)
    A(sw, 1, rot, 0)
    A(p_ang_n, 0, rot, 2)
    A(rot, 3, frac, 0)
    A(frac, 1, sub_c, 0)
    A(sub_c, 2, ln, 0)
    dists.append(ln)

# pesos según hacia dónde mira la cara: |normal|^nitidez, normalizados
nor_os = N('NormalVectorNode', -3550, 1700, extra={'m_Space': 0}, grupo=g3)
abs_n = N('AbsoluteNode', -3330, 1700, grupo=g3)
p_nit_n = P(p_nit, -3330, 1830, grupo=g3)
pow_n3 = N('PowerNode', -3110, 1700, grupo=g3)
split_w = N('SplitNode', -2890, 1700, grupo=g3)
A(nor_os, 0, abs_n, 0)
A(abs_n, 1, pow_n3, 0)
A(p_nit_n, 0, pow_n3, 1)
A(pow_n3, 2, split_w, 0)
suma = None
acum = None
for i, d in enumerate(dists):
    m = N('MultiplyNode', -1790, 1050 + i * 200, grupo=g3)
    A(d, 1, m, 0)
    A(split_w, i + 1, m, 1)
    if acum is None:
        acum, wsum = (m, 2), (split_w, i + 1)
    else:
        a = N('AddNode', -1600, 1100 + i * 200, grupo=g3)
        A(acum[0], acum[1], a, 0)
        A(m, 2, a, 1)
        acum = (a, 2)
        s = N('AddNode', -2670, 1750 + i * 100, grupo=g3)
        A(wsum[0], wsum[1], s, 0)
        A(split_w, i + 1, s, 1)
        wsum = (s, 2)
dist_tri = N('DivideNode', -1400, 1300, grupo=g3)                              # distancia mezclada
A(acum[0], acum[1], dist_tri, 0)
A(wsum[0], wsum[1], dist_tri, 1)
G.nota('Triplanar: la trama se proyecta desde los 3 ejes del objeto y se elige según la normal. '
       'En un cubo cada cara usa exactamente una proyección (puntos cuadrados y sin estirar); '
       'en curvas se mezclan. Se multiplica por la escala del objeto para que la densidad no '
       'cambie al escalarlo. Nitidez alta = transición más corta entre proyecciones.',
       -3550, 1950, 460, 120, g3)

# ================= 4) Tinta: puntos halftone ==================================
g4 = G.grupo('4) Tinta: puntos (zona clara limpia)', -1900, 700)
p_int_n = P(p_int, -1850, 900, grupo=g4)
p_suav_n = P(p_suav, -1850, 780, grupo=g4)
p_upun_n = P(p_upun, -1400, 820, grupo=g4)
s_u = N('SubtractNode', -1180, 760, grupo=g4)          # D - umbral
s_t = N('SaturateNode', -980, 760, grupo=g4)
m_r = N('MultiplyNode', -800, 760, grupo=g4)           # radio del punto
s_d = N('SubtractNode', -600, 760, grupo=g4)           # distancia - radio
d_s = N('DivideNode', -400, 760, grupo=g4)             # / suavizado
m_k = N('SaturateNode', -200, 760, grupo=g4)           # 0 = tinta, 1 = papel
A(one_minus, 1, s_u, 0)
A(p_upun_n, 0, s_u, 1)
A(s_u, 2, s_t, 0)
A(s_t, 1, m_r, 0)
A(p_int_n, 0, m_r, 1)
A(dist_tri, 2, s_d, 0)
A(m_r, 2, s_d, 1)
A(s_d, 2, d_s, 0)
A(p_suav_n, 0, d_s, 1)
A(d_s, 2, m_k, 0)

# Zona clara limpia: floor(banda) = 1 solo en la banda más iluminada → ahí se fuerza "papel".
floor_top = N('FloorNode', -600, 1000, grupo=g4)
p_limp_n = P(p_limp, -600, 1140, grupo=g4)
mul_limp = N('MultiplyNode', -400, 1000, grupo=g4)
min2 = N('MaximumNode', 0, 900, grupo=g4)              # máscara final de tinta
A(banda, 1, floor_top, 0)
A(floor_top, 1, mul_limp, 0)
A(p_limp_n, 0, mul_limp, 1)
A(m_k, 1, min2, 0)
A(mul_limp, 2, min2, 1)
G.nota('Puntos: distancia al centro de la celda < radio → tinta. Radio = (D - Umbral)·Intensidad. '
       'Limpiar Zona Clara: Floor(banda) vale 1 solo en la banda más clara; Maximum la deja '
       'sin puntos (0 = desactivado, 1 = limpia).',
       -1850, 1250, 460, 100, g4)

# ================= 5) Color toon + tinta ======================================
g5 = G.grupo('5) Color toon + tinta', 300, 300)
for o in G.nodos_plantilla('SampleTexture2DNode'):
    G.pos(o, 350, 500)
G.pos(G.nodo_prop_plantilla(G.prop_tex), 350, 420)
G.pos(G.nodo_prop_plantilla(G.prop_color), 600, 720)
G.pos(G.mult_tex, 600, 500)
p_somb_n = P(p_sombra, 820, 720, grupo=g5)
mul_somb = N('MultiplyNode', 1020, 620, grupo=g5)
lerp_toon = N('LerpNode', 1240, 480, grupo=g5)
mul_luz = N('MultiplyNode', 1460, 480, grupo=g5)                               # × color de la luz
p_tin_n = P(p_tinta, 1460, 360, grupo=g5)
lerp_tin = N('LerpNode', 1680, 420, grupo=g5)
A(G.mult_tex, 2, mul_somb, 0)
A(p_somb_n, 0, mul_somb, 1)
A(mul_somb, 2, lerp_toon, 0)
A(G.mult_tex, 2, lerp_toon, 1)
A(banda, 1, lerp_toon, 2)
A(lerp_toon, 3, mul_luz, 0)
A(luz, 2, mul_luz, 1)
A(p_tin_n, 0, lerp_tin, 0)
A(mul_luz, 2, lerp_tin, 1)
A(min2, 2, lerp_tin, 2)

# ================= 6) Luz de borde (rim) ======================================
g6 = G.grupo('6) Luz de borde', 300, -600)
view = N('ViewDirectionNode', 350, -500, grupo=g6)                             # mundo
dot_nv = N('DotProductNode', 580, -500, grupo=g6)
sat_nv = N('SaturateNode', 800, -500, grupo=g6)
om_nv = N('OneMinusNode', 1000, -500, grupo=g6)                                # 1 - N·V
p_ab_n = P(p_abor, 580, -320, grupo=g6)
om_ab = N('OneMinusNode', 800, -320, grupo=g6)                                 # borde1
add_ab = N('AddNode', 1000, -320, valores={1: v4(0.04)}, grupo=g6)             # borde2
smooth_r = N('SmoothstepNode', 1220, -500, grupo=g6)
mul_rb = N('MultiplyNode', 1440, -500, grupo=g6)                               # solo en banda iluminada
p_cb_n = P(p_cbor, 1440, -300, grupo=g6)
lerp_rim = N('LerpNode', 1900, 300, grupo=g6)
A(normal, 0, dot_nv, 0)
A(view, 0, dot_nv, 1)
A(dot_nv, 2, sat_nv, 0)
A(sat_nv, 1, om_nv, 0)
A(p_ab_n, 0, om_ab, 0)
A(om_ab, 1, smooth_r, 0)
A(om_ab, 1, add_ab, 0)
A(add_ab, 2, smooth_r, 1)
A(om_nv, 1, smooth_r, 2)
A(smooth_r, 3, mul_rb, 0)
A(banda, 1, mul_rb, 1)
A(lerp_tin, 3, lerp_rim, 0)
A(p_cb_n, 0, lerp_rim, 1)
A(mul_rb, 2, lerp_rim, 2)
G.nota('Fresnel simple: 1 - N·V es 1 en la silueta. Smoothstep lo vuelve un filo duro '
       'y se multiplica por la banda para que solo brille del lado de la luz.',
       350, -180, 420, 80, g6)

# ================= 7) Brillo especular duro ===================================
g7 = G.grupo('7) Brillo especular duro', 300, -1150)
add_h = N('AddNode', 350, -1050, grupo=g7)                                     # Dir + V
norm_h = N('NormalizeNode', 570, -1050, grupo=g7)                              # H
dot_nh = N('DotProductNode', 790, -1050, grupo=g7)
sat_nh = N('SaturateNode', 1010, -1050, grupo=g7)
p_br_n = P(p_bri, 1010, -880, grupo=g7)
pow_n = N('PowerNode', 1230, -1050, grupo=g7)
smooth_s = N('SmoothstepNode', 1450, -1050, valores={0: v4(0.45), 1: v4(0.55)}, grupo=g7)
mul_ss = N('MultiplyNode', 1670, -1050, grupo=g7)                              # × sombra proyectada
p_cbr_n = P(p_cbri, 1670, -880, grupo=g7)
lerp_bri = N('LerpNode', 2120, 300, grupo=g7)
A(luz, 1, add_h, 0)
A(view, 0, add_h, 1)
A(add_h, 2, norm_h, 0)
A(normal, 0, dot_nh, 0)
A(norm_h, 1, dot_nh, 1)
A(dot_nh, 2, sat_nh, 0)
A(sat_nh, 1, pow_n, 0)
A(p_br_n, 0, pow_n, 1)
A(pow_n, 2, smooth_s, 2)
A(smooth_s, 3, mul_ss, 0)
A(luz, 3, mul_ss, 1)
A(lerp_rim, 3, lerp_bri, 0)
A(p_cbr_n, 0, lerp_bri, 1)
p_fbr_n = P(p_fbri, 1670, -760, grupo=g7)
mul_fb = N('MultiplyNode', 1890, -1050, grupo=g7)                              # × Fuerza Brillo
A(mul_ss, 2, mul_fb, 0)
A(p_fbr_n, 0, mul_fb, 1)
A(mul_fb, 2, lerp_bri, 2)
A(lerp_bri, 3, G.base_color, 0)
G.nota('Blinn-Phong: H = normalize(Dir + V), (N·H)^Brillo. Smoothstep lo convierte en una '
       'mancha plana de borde duro. Más Brillo = mancha más pequeña.',
       350, -880, 420, 80, g7)

G.guardar(os.path.join(PROYECTO, 'Assets/Shaders/ToonComicEstilizado.shadergraph'))
