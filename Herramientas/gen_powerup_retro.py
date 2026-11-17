#!/usr/bin/env python3
"""Genera Assets/Shaders/PowerUpRetro.shadergraph: power-up de videojuego antiguo (URP Unlit opaco).
Vértices:
- onda de refresco que recorre el objeto de abajo a arriba e infla la malla al pasar
- glitch: franjas horizontales que se desplazan de lado de vez en cuando
- el ítem gira y flota solo, y tiembla como en PS1 (vértices ajustados a una rejilla de pantalla)
Color:
- separación RGB durante el glitch, paleta limitada con dither Bayer 4x4 y ciclo de colores
- emisión HDR pulsante (Fresnel) + brillo en la onda -> brilla con Bloom
- scanlines y estática pixelada en espacio de pantalla
- propiedad _ColorBordes para el contorno de MascaraBordesFeature
También crea el .meta del shader y el material M_PowerUpRetro si todavía no existen."""
import os
import uuid
from sg_comun import Grafo, PROYECTO, v4
from retro_comun import (preparar, escalar, funcion, S, props_compartidas, props_onda,
                         props_glitch, cadena_vertices, ONDA, ONDA_IO, GLITCH, GLITCH_IO)

G = Grafo('Proyecto Final/Efectos')
N, A, P = G.nodo, G.arista, G.prop_nodo
preparar(G)


# ------------------------------------------------------------------ propiedades
G.prop_color.update({'m_Value': {'r': 1.0, 'g': 0.8, 'b': 0.25, 'a': 1.0}})
p_cemi = G.prop_color_nueva('Color Emision', '_ColorEmision', (2.0, 1.3, 0.3, 1), hdr=True)
# Líneas Borderlands de este material (las lee MascaraBordesFeature). Alfa 0 = sin líneas.
p_bordes = G.prop_color_nueva('Color Bordes', '_ColorBordes', (0.02, 0.015, 0.03, 1))
p_iemi = G.prop_float('Intensidad Emision', '_IntensidadEmision', 1.5, 0, 10)
p_bbase = G.prop_float('Brillo Base', '_BrilloBase', 0.25, 0, 2)
p_fres = G.prop_float('Potencia Fresnel', '_PotenciaFresnel', 2.5, 0.1, 10)
p_pulso = G.prop_float('Pulso', '_Pulso', 0.5, 0, 1)
p_vpulso = G.prop_float('Velocidad Pulso', '_VelocidadPulso', 8, 0, 30)
# onda, glitch e ítem: compartidas con CopiaGlitch (retro_comun.py)
pr = props_compartidas(G)
p_aflot, p_vflot = pr['aflot'], pr['vflot']
p_iref = G.prop_float('Intensidad Refresco', '_IntensidadRefresco', 1.5, 0, 5)
p_rgb = G.prop_float('Separacion RGB', '_SeparacionRGB', 0.01, 0, 0.05)
# color retro
p_niv = G.prop_float('Niveles Color', '_NivelesColor', 4, 2, 32)
p_tbay = G.prop_float('Tamano Bayer', '_TamanoBayer', 2, 1, 8)
p_arco = G.prop_float('Arcoiris', '_Arcoiris', 0.5, 0, 1)
p_varco = G.prop_float('Velocidad Arcoiris', '_VelocidadArcoiris', 1.5, 0, 10)
p_gscan = G.prop_float('Grosor Scanline', '_GrosorScanline', 3, 1, 16)
p_iscan = G.prop_float('Intensidad Scanlines', '_IntensidadScanlines', 0.35, 0, 1)
p_truido = G.prop_float('Tamano Ruido', '_TamanoRuido', 2, 1, 16)
p_fruido = G.prop_float('FPS Ruido', '_FPSRuido', 15, 1, 60)
p_iruido = G.prop_float('Intensidad Ruido', '_IntensidadRuido', 0.12, 0, 1)

# ------------------------------------------------------------- Custom Functions
BAYER = r'''float bayer[16] = {0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5};
uint2 q = (uint2)fmod(floor(Pixel.xy), 4.0);
float umbral = (bayer[q.y * 4 + q.x] + 0.5) / 16.0;
float n = max(Niveles - 1.0, 1.0);
Out = floor(Color * n + umbral) / n;'''
BAYER_IO = ([('Color', 'float3'), ('Pixel', 'float3'), ('Niveles', 'float')], [('Out', 'float3')])

# ================= 0) Pantalla y tiempo (compartidos) ==========================
g0 = G.grupo('0) Pantalla y tiempo', -3400, -1500)
sp = N('ScreenPositionNode', -3350, -1400, grupo=g0)                           # 0..1 en pantalla
sw = N('SwizzleNode', -3150, -1400, grupo=g0)                                  # xy
scr = N('ScreenNode', -3350, -1240, grupo=g0)
res = N('CombineNode', -3150, -1240, grupo=g0)                                 # (ancho, alto)
px = N('MultiplyNode', -2950, -1360, grupo=g0)                                 # posición en píxeles
px_s = N('SplitNode', -2750, -1360, grupo=g0)                                  # y en píxeles
tiempo = N('TimeNode', -3350, -1080, grupo=g0)
A(sp, 0, sw, 0)
A(scr, 0, res, 0)
A(scr, 1, res, 1)
A(sw, 1, px, 0)
A(res, 6, px, 1)
A(px, 2, px_s, 0)

# ================= 1) Vértices =================================================
vert = cadena_vertices(G, pr, tiempo)
A(vert, S(vert, 'Posicion'), G.vert_pos, 0)

# ================= 2) Color retro ==============================================
g2 = G.grupo('2) Color: separación RGB, dither Bayer y ciclo de colores', -3400, -900)
# la onda y el glitch se recalculan en el fragment (descontando el flotar) para coincidir
t_fl = N('MultiplyNode', -3350, -300, grupo=g2)
sen_fl = N('SineNode', -3150, -300, grupo=g2)
p_aflot_n = P(p_aflot, -3150, -160, grupo=g2)
flot = N('MultiplyNode', -2950, -300, grupo=g2)                                # desplazamiento Y
A(tiempo, 0, t_fl, 0)
A(P(p_vflot, -3350, -160, grupo=g2), 0, t_fl, 1)
A(t_fl, 2, sen_fl, 0)
A(sen_fl, 1, flot, 0)
A(p_aflot_n, 0, flot, 1)
pos_os_f = N('PositionNode', -2950, -480, extra={'m_Space': 0}, grupo=g2)
onda_f = funcion(G, 'OndaRefresco', ONDA, *ONDA_IO, -2700, -400, g2)
A(pos_os_f, 0, onda_f, S(onda_f, 'PosOS'))
A(flot, 2, onda_f, S(onda_f, 'DesplazY'))
A(tiempo, 0, onda_f, S(onda_f, 'Tiempo'))
for i, (prop, nom) in enumerate(props_onda(pr)):
    A(P(prop, -2950, -120 + 60 * i, grupo=g2), 0, onda_f, S(onda_f, nom))
glitch_f = funcion(G, 'GlitchFranjas', GLITCH, *GLITCH_IO, -2400, -300, g2)
A(onda_f, S(onda_f, 'Altura'), glitch_f, S(glitch_f, 'Altura'))
A(tiempo, 0, glitch_f, S(glitch_f, 'Tiempo'))
for i, (prop, nom) in enumerate(props_glitch(pr)):
    A(P(prop, -2700, 200 + 60 * i, grupo=g2), 0, glitch_f, S(glitch_f, nom))

# UV desplazadas para R y B
p_rgb_n = P(p_rgb, -2400, -100, grupo=g2)
m_rgb = N('MultiplyNode', -2200, -250, grupo=g2)                               # glitch × separación
off = N('CombineNode', -2000, -250, grupo=g2)                                  # (o, 0)
uv = N('UVNode', -2200, -480, grupo=g2)
uv_sw = N('SwizzleNode', -2000, -480, grupo=g2)                                # xy
uv_r = N('AddNode', -1800, -520, grupo=g2)
uv_b = N('SubtractNode', -1800, -360, grupo=g2)
A(glitch_f, S(glitch_f, 'Glitch'), m_rgb, 0)
A(p_rgb_n, 0, m_rgb, 1)
A(m_rgb, 2, off, 0)
A(uv, 0, uv_sw, 0)
A(uv_sw, 1, uv_r, 0)
A(off, 6, uv_r, 1)
A(uv_sw, 1, uv_b, 0)
A(off, 6, uv_b, 1)

tex_n = G.nodo_prop_plantilla(G.prop_tex)
samp_g = G.nodos_plantilla('SampleTexture2DNode')[0]
G.pos(tex_n, -1850, -800)
G.pos(samp_g, -1600, -800)
G.pos(G.nodo_prop_plantilla(G.prop_color), -1150, -600)
G.pos(G.mult_tex, -950, -750)
samp_r = N('SampleTexture2DNode', -1600, -560, grupo=g2)
samp_b = N('SampleTexture2DNode', -1600, -320, grupo=g2)
A(tex_n, 0, samp_r, 1)
A(tex_n, 0, samp_b, 1)
A(uv_r, 2, samp_r, 2)
A(uv_b, 2, samp_b, 2)
rgb = N('CombineNode', -1350, -560, grupo=g2)                                  # R+, G, B-
A(samp_r, 4, rgb, 0)
A(samp_g, 5, rgb, 1)
A(samp_b, 6, rgb, 2)
# la plantilla conecta Sample.RGBA -> Multiply; ahora entra la mezcla RGB
G.g['m_Edges'] = [e for e in G.g['m_Edges']
                  if not (e['m_OutputSlot']['m_Node']['m_Id'] == samp_g['m_ObjectId']
                          and e['m_InputSlot']['m_Node']['m_Id'] == G.mult_tex['m_ObjectId'])]
A(rgb, 5, G.mult_tex, 0)

# dither Bayer
p_tbay_n = P(p_tbay, -950, -400, grupo=g2)
d_bay = N('DivideNode', -750, -450, grupo=g2)                                  # píxel / tamaño
p_niv_n = P(p_niv, -750, -300, grupo=g2)
bayer = funcion(G, 'PaletaBayer', BAYER, *BAYER_IO, -550, -700, g2)
A(px, 2, d_bay, 0)
A(p_tbay_n, 0, d_bay, 1)
A(G.mult_tex, 2, bayer, S(bayer, 'Color'))
A(d_bay, 2, bayer, S(bayer, 'Pixel'))
A(p_niv_n, 0, bayer, S(bayer, 'Niveles'))

# ciclo de colores
p_varco_n = P(p_varco, -550, -400, grupo=g2)
t_arco = N('MultiplyNode', -350, -450, grupo=g2)
hue = N('HueNode', -150, -650, extra={'m_HueMode': 1}, grupo=g2)              # offset normalizado
p_arco_n = P(p_arco, -150, -450, grupo=g2)
l_arco = N('LerpNode', 50, -700, grupo=g2)
A(tiempo, 0, t_arco, 0)
A(p_varco_n, 0, t_arco, 1)
A(bayer, S(bayer, 'Out'), hue, 0)
A(t_arco, 2, hue, 1)
A(bayer, S(bayer, 'Out'), l_arco, 0)
A(hue, 2, l_arco, 1)
A(p_arco_n, 0, l_arco, 2)
G.nota('Durante el glitch, R y B se leen desplazados en UV (separación RGB). Bayer: paleta de '
       '"Niveles Color" por canal con un patrón de dither 4x4 en píxeles de "Tamano Bayer". '
       'Hue gira el tono con el tiempo; Arcoiris mezcla el ciclo de colores.',
       -1850, -1000, 460, 90, g2)

# ================= 3) Scanlines ================================================
g3 = G.grupo('3) Scanlines (líneas horizontales de la tele)', -900, 300)
p_gscan_n = P(p_gscan, -850, 500, grupo=g3)
d_scan = N('DivideNode', -650, 400, grupo=g3)                                  # y px / grosor
fr_scan = N('FractionNode', -450, 400, grupo=g3)
st_scan = N('StepNode', -250, 400, valores={0: v4(0.5)}, grupo=g3)             # 0 / 1 alternado
p_iscan_n = P(p_iscan, -250, 560, grupo=g3)
m_scan = N('MultiplyNode', -50, 400, grupo=g3)
scan = N('OneMinusNode', 150, 400, grupo=g3)                                   # 1 o 1-intensidad
A(px_s, 2, d_scan, 0)
A(p_gscan_n, 0, d_scan, 1)
A(d_scan, 2, fr_scan, 0)
A(fr_scan, 1, st_scan, 1)
A(st_scan, 2, m_scan, 0)
A(p_iscan_n, 0, m_scan, 1)
A(m_scan, 2, scan, 0)

# ================= 4) Ruido / estática =========================================
g4 = G.grupo('4) Ruido: estática pixelada a pocos FPS', -900, 750)
p_truido_n = P(p_truido, -850, 930, grupo=g4)
d_ru = N('DivideNode', -650, 850, grupo=g4)
fl_ru = N('FloorNode', -450, 850, grupo=g4)                                    # celda de ruido
p_fruido_n = P(p_fruido, -850, 1050, grupo=g4)
t_ru = N('MultiplyNode', -650, 1050, grupo=g4)
semilla = N('FloorNode', -450, 1050, grupo=g4)                                 # cambia FPS veces/s
ruido = G.funcion('RuidoPixel',
                  'float2 p = Pixel.xy + Semilla * float2(37.13, 17.71);\n'
                  'Out = frac(sin(dot(p, float2(12.9898, 78.233))) * 43758.5453);',
                  [('Pixel', 'float3'), ('Semilla', 'float')], [('Out', 'float')],
                  -250, 900, g4)
c_ru = N('SubtractNode', -50, 900, valores={1: v4(0.5)}, grupo=g4)             # -0.5..0.5
p_iruido_n = P(p_iruido, -50, 1050, grupo=g4)
m_ru = N('MultiplyNode', 150, 900, grupo=g4)
A(px, 2, d_ru, 0)
A(p_truido_n, 0, d_ru, 1)
A(d_ru, 2, fl_ru, 0)
A(tiempo, 0, t_ru, 0)
A(p_fruido_n, 0, t_ru, 1)
A(t_ru, 2, semilla, 0)
A(fl_ru, 1, ruido, 0)
A(semilla, 1, ruido, 1)
A(ruido, 2, c_ru, 0)
A(c_ru, 2, m_ru, 0)
A(p_iruido_n, 0, m_ru, 1)

# ================= 5) Emisión ==================================================
g5 = G.grupo('5) Emisión: silueta + pulso + onda (HDR -> Bloom)', -900, 1250)
p_fres_n = P(p_fres, -850, 1350, grupo=g5)
fres = N('FresnelNode', -650, 1350, grupo=g5)
p_bbase_n = P(p_bbase, -650, 1530, grupo=g5)
a_bril = N('AddNode', -450, 1400, grupo=g5)                                    # fresnel + base
p_vpulso_n = P(p_vpulso, -850, 1650, grupo=g5)
t_pul = N('MultiplyNode', -650, 1650, grupo=g5)
sen = N('SineNode', -450, 1650, grupo=g5)
m_pul = N('MultiplyNode', -250, 1650, valores={1: escalar(0.5)}, grupo=g5)
a_pul = N('AddNode', -50, 1650, valores={1: v4(0.5)}, grupo=g5)                # 0..1
p_pulso_n = P(p_pulso, -250, 1800, grupo=g5)
om_pul = N('OneMinusNode', -50, 1800, grupo=g5)
l_pul = N('LerpNode', 150, 1700, valores={1: v4(1)}, grupo=g5)                 # 1-Pulso .. 1
p_iemi_n = P(p_iemi, -250, 1530, grupo=g5)
m_e2 = N('MultiplyNode', -50, 1400, grupo=g5)                                  # × intensidad
emi_esc = N('MultiplyNode', 350, 1450, grupo=g5)                               # × pulso
# brillo de la onda
sat_onda = N('SaturateNode', -650, 1950, grupo=g5)
p_iref_n = P(p_iref, -650, 2080, grupo=g5)
m_onda = N('MultiplyNode', -450, 1950, grupo=g5)
a_total = N('AddNode', 550, 1550, grupo=g5)                                    # cantidad de brillo
p_cemi_n = P(p_cemi, 550, 1750, grupo=g5)
emision = N('MultiplyNode', 750, 1550, grupo=g5)                               # × Color Emision
A(p_fres_n, 0, fres, 2)
A(fres, 3, a_bril, 0)
A(p_bbase_n, 0, a_bril, 1)
A(tiempo, 0, t_pul, 0)
A(p_vpulso_n, 0, t_pul, 1)
A(t_pul, 2, sen, 0)
A(sen, 1, m_pul, 0)
A(m_pul, 2, a_pul, 0)
A(p_pulso_n, 0, om_pul, 0)
A(om_pul, 1, l_pul, 0)
A(a_pul, 2, l_pul, 2)
A(a_bril, 2, m_e2, 0)
A(p_iemi_n, 0, m_e2, 1)
A(m_e2, 2, emi_esc, 0)
A(l_pul, 3, emi_esc, 1)
A(onda_f, S(onda_f, 'Onda'), sat_onda, 0)
A(sat_onda, 1, m_onda, 0)
A(p_iref_n, 0, m_onda, 1)
A(emi_esc, 2, a_total, 0)
A(m_onda, 2, a_total, 1)
A(a_total, 2, emision, 0)
A(p_cemi_n, 0, emision, 1)
G.nota('URP Unlit no usa el bloque Emission: el brillo se suma al Base Color con valores HDR '
       '(> 1). Activa Bloom en el Volume para que se vea el resplandor. La onda también brilla.',
       -850, 2200, 420, 80, g5)

# ================= 6) Color final ==============================================
g6 = G.grupo('6) Color final', 900, -300)
m_scan_c = N('MultiplyNode', 950, -200, grupo=g6)                              # color × scanlines
a_emi = N('AddNode', 1150, -150, grupo=g6)
a_ru = N('AddNode', 1350, -100, grupo=g6)
A(l_arco, 3, m_scan_c, 0)
A(scan, 1, m_scan_c, 1)
A(m_scan_c, 2, a_emi, 0)
A(emision, 2, a_emi, 1)
A(a_emi, 2, a_ru, 0)
A(m_ru, 2, a_ru, 1)
A(a_ru, 2, G.base_color, 0)
G.nota('Final = color retro × scanlines + emisión (silueta, pulso y onda) + ruido.',
       950, 50, 420, 60, g6)
G.g['m_VertexContext']['m_Position'] = {'x': 1600.0, 'y': 1900.0}
G.g['m_FragmentContext']['m_Position'] = {'x': 1600.0, 'y': -300.0}

SALIDA = os.path.join(PROYECTO, 'Assets/Shaders/PowerUpRetro.shadergraph')
G.guardar(SALIDA)

# ------------------------------------------------- .meta y material (solo si faltan)
meta = SALIDA + '.meta'
if not os.path.exists(meta):
    with open(meta, 'w') as f:
        f.write(f'fileFormatVersion: 2\nguid: {uuid.uuid4().hex}\nScriptedImporter:\n'
                '  internalIDToNameTable: []\n  externalObjects: {}\n  serializedVersion: 2\n'
                '  userData: \n  assetBundleName: \n  assetBundleVariant: \n'
                '  script: {fileID: 11500000, guid: 625f186215c104763be7675aa2d941aa, type: 3}\n')
guid_shader = next(l.split()[1] for l in open(meta) if l.startswith('guid:'))

mat = os.path.join(PROYECTO, 'Assets/Materiales/M_PowerUpRetro.mat')
if not os.path.exists(mat):
    with open(mat, 'w') as f:
        f.write('%YAML 1.1\n%TAG !u! tag:unity3d.com,2011:\n--- !u!21 &2100000\nMaterial:\n'
                '  serializedVersion: 8\n  m_ObjectHideFlags: 0\n'
                '  m_CorrespondingSourceObject: {fileID: 0}\n  m_PrefabInstance: {fileID: 0}\n'
                '  m_PrefabAsset: {fileID: 0}\n  m_Name: M_PowerUpRetro\n'
                f'  m_Shader: {{fileID: -6465566751694194690, guid: {guid_shader}, type: 3}}\n'
                '  m_Parent: {fileID: 0}\n  m_ModifiedSerializedProperties: 0\n'
                '  m_ValidKeywords: []\n  m_InvalidKeywords: []\n  m_LightmapFlags: 4\n'
                '  m_EnableInstancingVariants: 0\n  m_DoubleSidedGI: 0\n  m_CustomRenderQueue: -1\n'
                '  stringTagMap: {}\n  disabledShaderPasses: []\n  m_LockedProperties: \n'
                '  m_SavedProperties:\n    serializedVersion: 3\n    m_TexEnvs: []\n'
                '    m_Ints: []\n    m_Floats: []\n    m_Colors: []\n'
                '  m_BuildTextureStacks: []\n  m_AllowLocking: 1\n')
    with open(mat + '.meta', 'w') as f:
        f.write(f'fileFormatVersion: 2\nguid: {uuid.uuid4().hex}\nNativeFormatImporter:\n'
                '  externalObjects: {}\n  mainObjectFileID: 2100000\n  userData: \n'
                '  assetBundleName: \n  assetBundleVariant: \n')
    print('creado', os.path.relpath(mat, PROYECTO))
