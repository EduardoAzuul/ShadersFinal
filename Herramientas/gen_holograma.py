#!/usr/bin/env python3
"""Genera Assets/Shaders/Hologram.shadergraph: holograma de energía (URP Unlit transparente).
Basado en HologramEnergyShader (subgrafo Hex Lattice + Fresnel + brillo en intersecciones),
pero con el patrón hexagonal también en la transparencia y todo expuesto en el material."""
import os
from sg_comun import Grafo, PROYECTO, cargar, v4

ORIGINAL = os.path.join(PROYECTO, 'Assets/Shaders/HologramEnergyShader.shadergraph')

G = Grafo('Proyecto Final/Efectos', con_textura=False)
G.target.update({'m_SurfaceType': 1, 'm_AlphaMode': 0, 'm_CastShadows': False,
                 'm_ReceiveShadows': False})
N, A, P = G.nodo, G.arista, G.prop_nodo

# plantillas del grafo original (subgrafo Hex Lattice y Fresnel)
orig = cargar(ORIGINAL)
oby = {o['m_ObjectId']: o for o in orig}
for tipo in ('SubGraphNode', 'FresnelNode'):
    n = next(o for o in orig if o['m_Type'].endswith('.' + tipo))
    G.T[tipo] = [None, n, [oby[s['m_Id']] for s in n['m_Slots']]]
alpha_block = next(o for o in G.objs if o.get('m_Name') == 'SurfaceDescription.Alpha')

# ------------------------------------------------------------------ propiedades
G.prop_color.update({'m_Name': 'Color Holograma', 'm_RefNameGeneratedByDisplayName': 'Color Holograma',
                     'm_ColorMode': 1, 'm_Value': {'r': 0.65, 'g': 0.98, 'b': 1.0, 'a': 1.0}})
p_int = G.prop_float('Intensidad', '_Intensidad', 2, 0, 10)
p_tile = G.prop_float('Escala Hexagonos', '_EscalaHexagonos', 10, 1, 50)
p_edge = G.prop_float('Grosor Lineas', '_GrosorLineas', 0.2, 0.01, 0.5)
p_lin = G.prop_float('Opacidad Lineas', '_OpacidadLineas', 0.8, 0, 1)
p_base = G.prop_float('Opacidad Base', '_OpacidadBase', 0.08, 0, 1)
p_fres = G.prop_float('Potencia Fresnel', '_PotenciaFresnel', 3, 0.1, 10)
p_zona = G.prop_float('Zona Interseccion', '_ZonaInterseccion', 4, 0.1, 20)

# ================= 1) Patrón hexagonal ========================================
g1 = G.grupo('1) Rejilla hexagonal (subgrafo Hex Lattice)', -1600, -400)
p_tile_n = P(p_tile, -1550, -300, grupo=g1)
tiling = N('CombineNode', -1350, -300, grupo=g1)                               # (escala, escala)
p_edge_n = P(p_edge, -1350, -120, grupo=g1)
hexs = N('SubGraphNode', -1100, -300, grupo=g1)
A(p_tile_n, 0, tiling, 0)
A(p_tile_n, 0, tiling, 1)
ids = {G.T['SubGraphNode'][2][i]['m_DisplayName']: G.T['SubGraphNode'][2][i]['m_Id'] for i in range(4)}
A(tiling, 6, hexs, ids['Tiling'])
A(p_edge_n, 0, hexs, ids['Edge Width'])

# ================= 2) Fresnel (silueta) =======================================
g2 = G.grupo('2) Fresnel: brillo en la silueta', -1600, 100)
p_fres_n = P(p_fres, -1550, 200, grupo=g2)
fres = N('FresnelNode', -1300, 200, grupo=g2)
A(p_fres_n, 0, fres, 2)

# ================= 3) Intersecciones ==========================================
g3 = G.grupo('3) Brillo donde toca otros objetos', -1600, 500)
sp = N('ScreenPositionNode', -1550, 600, extra={'m_ScreenSpaceType': 1}, grupo=g3)   # Raw: w = profundidad
split = N('SplitNode', -1350, 600, grupo=g3)
depth = N('SceneDepthNode', -1350, 760, extra={'m_DepthSamplingMode': 2}, grupo=g3) # Eye
dif = N('SubtractNode', -1150, 680, grupo=g3)                                  # escena - fragmento
p_zona_n = P(p_zona, -1150, 850, grupo=g3)
mz = N('MultiplyNode', -950, 680, grupo=g3)
ss = N('SmoothstepNode', -750, 680, valores={0: v4(0), 1: v4(1)}, grupo=g3)
inter = N('OneMinusNode', -550, 680, grupo=g3)                                 # 1 junto al contacto
A(sp, 0, split, 0)
A(depth, 1, dif, 0)
A(split, 4, dif, 1)
A(dif, 2, mz, 0)
A(p_zona_n, 0, mz, 1)
A(mz, 2, ss, 2)
A(ss, 3, inter, 0)
G.nota('Profundidad de la escena detrás del holograma menos la profundidad del holograma: '
       'cerca de 0 donde atraviesa otro objeto. Zona Interseccion alto = franja más delgada.',
       -1550, 950, 420, 80, g3)

# ================= 4) Combinar ================================================
g4 = G.grupo('4) Transparencia y color', -400, -100)
p_lin_n = P(p_lin, -350, -100, grupo=g4)
m_hex = N('MultiplyNode', -150, -200, grupo=g4)                                # líneas × opacidad
p_base_n = P(p_base, -150, -20, grupo=g4)
a1 = N('AddNode', 50, -150, grupo=g4)
a2 = N('AddNode', 250, -50, grupo=g4)
a3 = N('AddNode', 450, 50, grupo=g4)
alfa = N('SaturateNode', 650, 50, grupo=g4)
A(hexs, 1, m_hex, 0)
A(p_lin_n, 0, m_hex, 1)
A(m_hex, 2, a1, 0)
A(p_base_n, 0, a1, 1)
A(a1, 2, a2, 0)
A(fres, 3, a2, 1)
A(a2, 2, a3, 0)
A(inter, 1, a3, 1)
A(a3, 2, alfa, 0)
A(alfa, 1, alpha_block, 0)

p_col_n = P(G.prop_color, 250, 300, grupo=g4)
p_int_n = P(p_int, 250, 420, grupo=g4)
color = N('MultiplyNode', 450, 300, grupo=g4)                                  # HDR: brilla con Bloom
A(p_col_n, 0, color, 0)
A(p_int_n, 0, color, 1)
A(color, 2, G.base_color, 0)
G.nota('Alpha = líneas hexagonales + opacidad base + fresnel + intersección. '
       'El color es HDR (× Intensidad) para que brille con Bloom.', -350, 500, 420, 80, g4)

G.guardar(os.path.join(PROYECTO, 'Assets/Shaders/Hologram.shadergraph'))
