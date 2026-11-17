#!/usr/bin/env python3
"""Genera Assets/Shaders/CopiaGlitch.shadergraph: copias desfasadas estilo Spider-Verse para
PowerUpRetro. Se usa como material EXTRA del mismo MeshRenderer (uno por copia):
- se deforma igual que PowerUpRetro (onda, glitch, giro/flotar, jitter: retro_comun.py)
- casco invertido (solo caras traseras) inflado y desplazado en pantalla: el objeto tapa el
  interior y solo asoma lo que sale por el borde de la silueta
- salta a una posición aleatoria unas cuantas veces por segundo
- pintada con su propia trama: puntos halftone, líneas diagonales o Bayer
Crea también el .meta y los materiales M_CopiaGlitch_Magenta / M_CopiaGlitch_Cian si faltan.
El componente CopiasGlitch.cs copia los valores compartidos del material principal."""
import os
import uuid
from sg_comun import Grafo, PROYECTO
from retro_comun import preparar, funcion, S, props_compartidas, props_glitch, cadena_vertices

G = Grafo('Proyecto Final/Efectos', con_textura=False)
G.target['m_RenderFace'] = 1        # Back: casco invertido, como ContornoComic
G.target['m_CastShadows'] = False
N, A, P = G.nodo, G.arista, G.prop_nodo
preparar(G)
alpha_block = G.alpha_clip(0.5)

# ------------------------------------------------------------------ propiedades
G.prop_color.update({'m_Name': 'Color Copia', 'm_RefNameGeneratedByDisplayName': 'Color Copia',
                     'm_DefaultReferenceName': '_Color_Copia', 'm_OverrideReferenceName': '_ColorCopia',
                     'm_ColorMode': 1, 'm_Value': {'r': 2.0, 'g': 0.2, 'b': 1.4, 'a': 1.0}})
p_fondo = G.prop_color_nueva('Color Fondo', '_ColorFondo', (0.05, 0.02, 0.08, 1))
p_int = G.prop_float('Intensidad', '_Intensidad', 1.5, 0, 10)
p_gros = G.prop_float('Grosor Copia', '_GrosorCopia', 0.004, 0, 0.03)
p_dx = G.prop_float('Desfase X', '_DesfaseX', 0.012, -0.1, 0.1)
p_dy = G.prop_float('Desfase Y', '_DesfaseY', 0.006, -0.1, 0.1)
p_salto = G.prop_float('Salto', '_Salto', 0.006, 0, 0.05)
p_fsalto = G.prop_float('FPS Salto', '_FPSSalto', 8, 1, 30)
p_patron = G.prop_float('Patron', '_Patron', 0, 0, 2)
p_tam = G.prop_float('Tamano Trama', '_TamanoTrama', 4, 1, 16)
p_dens = G.prop_float('Densidad', '_Densidad', 0.5, 0, 1)
p_recorte = G.prop_float('Recortar Trama', '_RecortarTrama', 1, 0, 1)
p_solo = G.prop_float('Solo Con Glitch', '_SoloConGlitch', 0, 0, 1)
# compartidas con PowerUpRetro (las sincroniza CopiasGlitch.cs)
pr = props_compartidas(G)

# ------------------------------------------------------------- Custom Functions
DESFASE = r'''float3 p = PosOS;
#if defined(SHADERGRAPH_PREVIEW)
p += NormalOS * GrosorCopia * 5.0;
p.xy += float2(DesfaseX, DesfaseY) * 2.0;
#else
// inflar por la dirección suave de VerticesRetro (× distancia a cámara: grosor parecido de cerca y de lejos)
float dist = distance(GetCameraPositionWS(), TransformObjectToWorld(p));
p += NormalOS * GrosorCopia * dist;
// desplazar en pantalla: desfase fijo + salto aleatorio que cambia FPSSalto veces por segundo
float4 cs = TransformObjectToHClip(p);
float s = floor(Tiempo * FPSSalto);
float2 azar = frac(sin(float2(s * 12.9898, s * 78.233) + 1.7) * 43758.5453) * 2.0 - 1.0;
float2 desf = float2(DesfaseX, DesfaseY) + azar * Salto;
desf.y *= _ProjectionParams.x;               // misma dirección aunque la proyección esté volteada
cs.xy += desf * 2.0 * cs.w;                  // clip va de -1 a 1: ×2 = fracción de pantalla
float4 ws = mul(UNITY_MATRIX_I_VP, cs);
p = TransformWorldToObject(ws.xyz / ws.w);
#endif
Posicion = p;'''
DESFASE_IO = ([('PosOS', 'float3'), ('NormalOS', 'float3'), ('GrosorCopia', 'float'),
               ('DesfaseX', 'float'), ('DesfaseY', 'float'), ('Salto', 'float'),
               ('FPSSalto', 'float'), ('Tiempo', 'float')], [('Posicion', 'float3')])

TRAMA = r'''float2 q = Pixel.xy / max(Tamano, 1.0);
float t;
if (Patron < 0.5)          // puntos halftone en rejilla a 45°
{
    float2 r = float2(q.x + q.y, q.x - q.y) * 0.70710678;
    t = step(length(frac(r) - 0.5), Densidad * 0.70710678);
}
else if (Patron < 1.5)     // líneas diagonales
{
    t = step(frac((q.x + q.y) * 0.5), Densidad);
}
else                       // Bayer 4x4
{
    float bayer[16] = {0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5};
    uint2 b = (uint2)fmod(floor(q), 4.0);
    t = step((bayer[b.y * 4 + b.x] + 0.5) / 16.0, Densidad);
}
// mismo "¿hay glitch en este cuadro?" que GlitchFranjas
float activo = step(1.0 - Probabilidad, frac(sin(floor(Tiempo * FPS) * 12.9898 + 4.1) * 43758.5453));
float visible = lerp(1.0, activo, SoloConGlitch);
Trama = t;
Alpha = visible * lerp(1.0, t, Recortar);'''
TRAMA_IO = ([('Pixel', 'float3'), ('Patron', 'float'), ('Tamano', 'float'), ('Densidad', 'float'),
             ('Recortar', 'float'), ('SoloConGlitch', 'float'), ('Tiempo', 'float'),
             ('FPS', 'float'), ('Probabilidad', 'float')], [('Trama', 'float'), ('Alpha', 'float')])

# ================= 0) Pantalla y tiempo ========================================
g0 = G.grupo('0) Pantalla y tiempo', -3400, -900)
sp = N('ScreenPositionNode', -3350, -800, grupo=g0)
sw = N('SwizzleNode', -3150, -800, grupo=g0)                                   # xy
scr = N('ScreenNode', -3350, -640, grupo=g0)
res = N('CombineNode', -3150, -640, grupo=g0)
px = N('MultiplyNode', -2950, -760, grupo=g0)                                  # píxeles
tiempo = N('TimeNode', -3350, -480, grupo=g0)
A(sp, 0, sw, 0)
A(scr, 0, res, 0)
A(scr, 1, res, 1)
A(sw, 1, px, 0)
A(res, 6, px, 1)

# ================= 1) Vértices (igual que PowerUpRetro) + desfase ==============
vert = cadena_vertices(G, pr, tiempo, '1) Vértices: igual que PowerUpRetro')
g1b = G.grupo('2) Copia: inflar, desplazar en pantalla y saltar', -1800, 1900)
desf = funcion(G, 'DesfaseCopia', DESFASE, *DESFASE_IO, -1500, 2000, g1b)
A(vert, S(vert, 'Posicion'), desf, S(desf, 'PosOS'))
A(vert, S(vert, 'DireccionSalida'), desf, S(desf, 'NormalOS'))
A(tiempo, 0, desf, S(desf, 'Tiempo'))
for i, (prop, nom) in enumerate([(p_gros, 'GrosorCopia'), (p_dx, 'DesfaseX'), (p_dy, 'DesfaseY'),
                                 (p_salto, 'Salto'), (p_fsalto, 'FPSSalto')]):
    A(P(prop, -1750, 2300 + 60 * i, grupo=g1b), 0, desf, S(desf, nom))
A(desf, S(desf, 'Posicion'), G.vert_pos, 0)
G.nota('Render Face = Back (casco invertido): el objeto principal tapa el interior de la copia y '
       'solo se ve lo que sale por el borde de la silueta. Desfase X/Y en fracción de pantalla; '
       'Salto mueve la copia a una posición aleatoria FPS Salto veces por segundo.',
       -1750, 2650, 460, 100, g1b)

# ================= 3) Trama ====================================================
g3 = G.grupo('3) Trama: puntos / líneas / Bayer', -2000, -500)
trama = funcion(G, 'TramaCopia', TRAMA, *TRAMA_IO, -1500, -400, g3)
A(px, 2, trama, S(trama, 'Pixel'))
A(tiempo, 0, trama, S(trama, 'Tiempo'))
for i, (prop, nom) in enumerate([(p_patron, 'Patron'), (p_tam, 'Tamano'), (p_dens, 'Densidad'),
                                 (p_recorte, 'Recortar'), (p_solo, 'SoloConGlitch')]):
    A(P(prop, -1800, -300 + 60 * i, grupo=g3), 0, trama, S(trama, nom))
for i, (prop, nom) in enumerate(props_glitch(pr)[1:]):                         # FPS y Probabilidad
    A(P(prop, -1800, 50 + 60 * i, grupo=g3), 0, trama, S(trama, nom))
G.nota('Patron: 0 = puntos halftone, 1 = líneas diagonales, 2 = Bayer 4x4 (en píxeles de '
       'Tamano Trama). Recortar Trama = 1 descarta los huecos (la copia queda hecha solo de la '
       'trama). Solo Con Glitch = 1: la copia solo aparece cuando el objeto hace glitch.',
       -1800, 200, 460, 100, g3)

# ================= 4) Color ====================================================
g4 = G.grupo('4) Color', -900, -500)
p_col_n = P(G.prop_color, -850, -400, grupo=g4)
p_int_n = P(p_int, -850, -320, grupo=g4)
col = N('MultiplyNode', -650, -400, grupo=g4)                                  # HDR -> Bloom
p_fondo_n = P(p_fondo, -650, -250, grupo=g4)
mezcla = N('LerpNode', -450, -350, grupo=g4)
A(p_col_n, 0, col, 0)
A(p_int_n, 0, col, 1)
A(p_fondo_n, 0, mezcla, 0)
A(col, 2, mezcla, 1)
A(trama, S(trama, 'Trama'), mezcla, 2)
A(mezcla, 3, G.base_color, 0)
A(trama, S(trama, 'Alpha'), alpha_block, 0)

SALIDA = os.path.join(PROYECTO, 'Assets/Shaders/CopiaGlitch.shadergraph')
G.guardar(SALIDA)

# ------------------------------------------------- .meta y materiales (solo si faltan)
meta = SALIDA + '.meta'
if not os.path.exists(meta):
    with open(meta, 'w') as f:
        f.write(f'fileFormatVersion: 2\nguid: {uuid.uuid4().hex}\nScriptedImporter:\n'
                '  internalIDToNameTable: []\n  externalObjects: {}\n  serializedVersion: 2\n'
                '  userData: \n  assetBundleName: \n  assetBundleVariant: \n'
                '  script: {fileID: 11500000, guid: 625f186215c104763be7675aa2d941aa, type: 3}\n')
guid_shader = next(l.split()[1] for l in open(meta) if l.startswith('guid:'))


def material(nombre, floats, colores):
    ruta = os.path.join(PROYECTO, f'Assets/Materiales/{nombre}.mat')
    if os.path.exists(ruta):
        return
    fl = ''.join(f'    - {k}: {v}\n' for k, v in floats.items())
    co = ''.join(f'    - {k}: {{r: {c[0]}, g: {c[1]}, b: {c[2]}, a: {c[3]}}}\n' for k, c in colores.items())
    with open(ruta, 'w') as f:
        f.write('%YAML 1.1\n%TAG !u! tag:unity3d.com,2011:\n--- !u!21 &2100000\nMaterial:\n'
                '  serializedVersion: 8\n  m_ObjectHideFlags: 0\n'
                '  m_CorrespondingSourceObject: {fileID: 0}\n  m_PrefabInstance: {fileID: 0}\n'
                f'  m_PrefabAsset: {{fileID: 0}}\n  m_Name: {nombre}\n'
                f'  m_Shader: {{fileID: -6465566751694194690, guid: {guid_shader}, type: 3}}\n'
                '  m_Parent: {fileID: 0}\n  m_ModifiedSerializedProperties: 0\n'
                '  m_ValidKeywords: []\n  m_InvalidKeywords: []\n  m_LightmapFlags: 4\n'
                '  m_EnableInstancingVariants: 0\n  m_DoubleSidedGI: 0\n  m_CustomRenderQueue: -1\n'
                '  stringTagMap: {}\n  disabledShaderPasses: []\n  m_LockedProperties: \n'
                '  m_SavedProperties:\n    serializedVersion: 3\n    m_TexEnvs: []\n'
                f'    m_Ints: []\n    m_Floats:\n{fl}    m_Colors:\n{co}'
                '  m_BuildTextureStacks: []\n  m_AllowLocking: 1\n')
    with open(ruta + '.meta', 'w') as f:
        f.write(f'fileFormatVersion: 2\nguid: {uuid.uuid4().hex}\nNativeFormatImporter:\n'
                '  externalObjects: {}\n  mainObjectFileID: 2100000\n  userData: \n'
                '  assetBundleName: \n  assetBundleVariant: \n')
    print('creado', os.path.relpath(ruta, PROYECTO))


material('M_CopiaGlitch_Magenta',
         {'_DesfaseX': 0.012, '_DesfaseY': 0.006, '_Patron': 0, '_TamanoTrama': 4, '_Densidad': 0.5},
         {'_ColorCopia': (2, 0.2, 1.4, 1), '_ColorFondo': (0.05, 0.02, 0.08, 1)})
material('M_CopiaGlitch_Cian',
         {'_DesfaseX': -0.012, '_DesfaseY': -0.006, '_Patron': 1, '_TamanoTrama': 3, '_Densidad': 0.45},
         {'_ColorCopia': (0.2, 1.6, 2, 1), '_ColorFondo': (0.02, 0.04, 0.08, 1)})
