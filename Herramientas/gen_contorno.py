#!/usr/bin/env python3
"""Genera Assets/Shaders/ContornoComic.shadergraph: contorno de tinta por casco invertido.
Se usa como SEGUNDO material del MeshRenderer."""
import os
from sg_comun import Grafo, PROYECTO

G = Grafo('Proyecto Final', con_textura=False)
G.target['m_RenderFace'] = 1        # Back: solo caras traseras (Cull Front)
G.target['m_CastShadows'] = False

G.prop_color.update({'m_Name': 'Color Contorno', 'm_RefNameGeneratedByDisplayName': 'Color Contorno',
                     'm_Value': {'r': 0.03, 'g': 0.02, 'b': 0.05, 'a': 1.0}})
p_grosor = G.prop_float('Grosor', '_Grosor', 0.004, 0, 0.02)

N, A, P = G.nodo, G.arista, G.prop_nodo

g1 = G.grupo('1) Inflar la malla en el vertex shader', -1500, -300)
pos_os = N('PositionNode', -1450, -200, extra={'m_Space': 0}, grupo=g1)       # objeto
nor_os = N('NormalVectorNode', -1450, -60, extra={'m_Space': 0}, grupo=g1)    # objeto
cam = N('CameraNode', -1450, 120, grupo=g1)
obj = N('ObjectNode', -1450, 330, grupo=g1)
dist = N('DistanceNode', -1200, 160, grupo=g1)                                 # distancia a cámara
p_gr_n = P(p_grosor, -1200, 20, grupo=g1)
mul_g = N('MultiplyNode', -1000, 60, grupo=g1)
mul_n = N('MultiplyNode', -800, -60, grupo=g1)
add_p = N('AddNode', -580, -200, grupo=g1)
A(cam, 0, dist, 0)
A(obj, 0, dist, 1)
A(p_gr_n, 0, mul_g, 0)
A(dist, 2, mul_g, 1)
p_cubo = G.prop_float('Modo Cubo', '_ModoCubo', 0, 0, 1)
p_cubo_n = P(p_cubo, -1450, -420, grupo=g1)
norm_pos = N('NormalizeNode', -1200, -300, grupo=g1)                          # dirección desde el centro
lerp_dir = N('LerpNode', -1000, -200, grupo=g1)
norm_dir = N('NormalizeNode', -800, -200, grupo=g1)
A(pos_os, 0, norm_pos, 0)
A(nor_os, 0, lerp_dir, 0)
A(norm_pos, 1, lerp_dir, 1)
A(p_cubo_n, 0, lerp_dir, 2)
A(lerp_dir, 3, norm_dir, 0)
A(norm_dir, 1, mul_n, 0)
A(mul_g, 2, mul_n, 1)
G.nota('Modo Cubo: en mallas con aristas duras cada esquina tiene 3 normales distintas y el '
       'contorno se abre. Con Modo Cubo = 1 se infla desde el centro del objeto (dirección = '
       'posición normalizada): las esquinas quedan unidas. Usa 0 para esferas/modelos suaves.',
       -1450, -620, 460, 100, g1)
A(pos_os, 0, add_p, 0)
A(mul_n, 2, add_p, 1)
A(add_p, 2, G.vert_pos, 0)
G.nota('Cada vértice se empuja hacia afuera por su normal. Se multiplica por la distancia a la '
       'cámara para que la línea mida casi lo mismo en pantalla de cerca y de lejos. '
       'En Graph Settings, Render Face = Back: solo se ven las caras traseras infladas, '
       'que asoman alrededor del objeto como contorno.', -1450, 480, 460, 120, g1)

g2 = G.grupo('2) Color de la tinta', -600, 150)
p_col_n = P(G.prop_color, -550, 250, grupo=g2)
A(p_col_n, 0, G.base_color, 0)

G.guardar(os.path.join(PROYECTO, 'Assets/Shaders/ContornoComic.shadergraph'))
