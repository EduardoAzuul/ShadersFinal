"""Piezas compartidas por PowerUpRetro y CopiaGlitch: nodos extra, Custom Functions de la
onda / glitch / vértices retro y sus propiedades. Las dos gráficas usan exactamente el mismo
HLSL y las mismas referencias, así la copia se deforma igual que el objeto."""
import os
from sg_comun import SG_PKG, cargar

# --- nodos que no están en nodes.json: se clonan de los Samples del paquete ---
EXTRA = {
    'TimeNode': 'Samples~/FeatureExamples/UV Projection/FlowMapping/FlowMapping.shadergraph',
    'SineNode': 'Samples~/FeatureExamples/VertexAnimation/AnimatedFlag/AnimatedFlag.shadergraph',
    'StepNode': 'Samples~/UGUIShaders/Examples/Simple Examples.shadergraph',
    'HueNode': 'Samples~/NodeReference/Artistic/Hue.shadergraph',
    'FresnelNode': 'Samples~/FeatureExamples/UV Projection/InteriorCubemapping/InteriorCubemapping.shadergraph',
}


def preparar(G):
    """Registra en G.T los nodos que no están en nodes.json (clonados de los Samples)."""
    for tipo, archivo in EXTRA.items():
        objs = cargar(os.path.join(SG_PKG, archivo))
        by = {o['m_ObjectId']: o for o in objs}
        n = next(o for o in objs if o['m_Type'].endswith('.' + tipo))
        G.T[tipo] = [None, n, [by[s['m_Id']] for s in n['m_Slots']]]


def escalar(valor):
    """Valor constante para la entrada B de un Multiply (slot de matriz dinámica)."""
    m = {f'e{i}{j}': 0.0 for i in range(4) for j in range(4)}
    m.update({f'e0{j}': float(valor) for j in range(4)})
    return m


def funcion(G, nombre, cuerpo, entradas, salidas, x, y, grupo):
    """G.funcion + diccionario nombre -> id de slot, para conectar por nombre."""
    n = G.funcion(nombre, cuerpo, entradas, salidas, x, y, grupo)
    SLOTS[n['m_ObjectId']] = {nom: i for i, (nom, _) in enumerate(list(entradas) + list(salidas))}
    return n


SLOTS = {}


def S(nodo, nombre):
    """Id del slot 'nombre' de una Custom Function creada con funcion()."""
    return SLOTS[nodo['m_ObjectId']][nombre]


ONDA = r'''float y = (PosOS.y - DesplazY - AlturaMin) / max(AlturaMax - AlturaMin, 1e-4);
float a = max(Ancho, 1e-3);
// el centro va de -ancho a 1+ancho: la banda entra y sale completa del objeto
float centro = lerp(-a, 1.0 + a, frac(Tiempo * Velocidad));
float d = (y - centro) / a;                 // -1..1 dentro de la banda
float b = saturate(1.0 - abs(d));
b = b * b * (3.0 - 2.0 * b);                // smoothstep
Onda = b * lerp(1.0, cos(6.2831853 * d), Ondulacion);
Altura = y;'''
ONDA_IO = ([('PosOS', 'float3'), ('DesplazY', 'float'), ('Tiempo', 'float'), ('Velocidad', 'float'),
            ('Ancho', 'float'), ('AlturaMin', 'float'), ('AlturaMax', 'float'), ('Ondulacion', 'float')],
           [('Onda', 'float'), ('Altura', 'float')])

GLITCH = r'''float s = floor(Tiempo * FPS);
// ¿hay glitch en este "cuadro"? (mismo valor para todo el objeto)
float activo = step(1.0 - Probabilidad, frac(sin(s * 12.9898 + 4.1) * 43758.5453));
float f = floor(Altura * Franjas);
float h = frac(sin(dot(float2(f, s), float2(127.1, 311.7))) * 43758.5453);
// la mitad de las franjas se mueve, cada una con su desplazamiento (-1..1)
Glitch = activo * step(0.5, h) * (h * 4.0 - 3.0);'''
GLITCH_IO = ([('Altura', 'float'), ('Tiempo', 'float'), ('Franjas', 'float'), ('FPS', 'float'),
              ('Probabilidad', 'float')], [('Glitch', 'float')])

VERTICES = r'''// dirección de inflado: en mallas con aristas duras cada esquina está repetida con normales
// distintas; empujar por la normal abre huecos. La dirección radial desde el centro es igual
// para todas las copias de la esquina, así la malla no se separa.
float3 centro = float3(0.0, 0.5 * (AlturaMin + AlturaMax), 0.0);
float3 radial = PosOS - centro;
radial = dot(radial, radial) > 1e-8 ? normalize(radial) : NormalOS;
float3 dir = normalize(lerp(NormalOS, radial, InfladoSuave) + 1e-5);
// 1) la onda infla la malla
float3 p = PosOS + dir * Onda * AmplitudOnda;
// 2) el ítem gira sobre Y y flota
float ang = radians(VelocidadGiro) * Tiempo;
float c = cos(ang), s = sin(ang);
float2x2 R = float2x2(c, -s, s, c);
p.xz = mul(R, p.xz);
float3 n = NormalOS;
n.xz = mul(R, n.xz);
dir.xz = mul(R, dir.xz);
p.y += sin(Tiempo * VelocidadFlotar) * AlturaFlotar;
#if defined(SHADERGRAPH_PREVIEW)
p.x += Glitch * FuerzaGlitch;
#else
// 3) glitch: la franja se mueve hacia la derecha de la cámara
p += TransformWorldToObjectDir(UNITY_MATRIX_V[0].xyz) * Glitch * FuerzaGlitch;
  #if !(defined(SHADERPASS_SHADOWCASTER) && SHADERPASS == SHADERPASS_SHADOWCASTER)
// 4) jitter PS1: el vértice se ajusta a una rejilla de baja resolución en pantalla
float4 cs = TransformObjectToHClip(p);
float2 rejilla = float2(ResolucionJitter * _ScreenParams.x / _ScreenParams.y, ResolucionJitter) * 0.5;
float4 ajustado = cs;
ajustado.xy = round(cs.xy / cs.w * rejilla) / rejilla * cs.w;
float4 ws = mul(UNITY_MATRIX_I_VP, ajustado);
p = lerp(p, TransformWorldToObject(ws.xyz / ws.w), Jitter);
  #endif
#endif
Posicion = p;
NormalSalida = n;
DireccionSalida = dir;'''
VERTICES_IO = ([('PosOS', 'float3'), ('NormalOS', 'float3'), ('Onda', 'float'), ('Glitch', 'float'),
                ('AmplitudOnda', 'float'), ('FuerzaGlitch', 'float'), ('Tiempo', 'float'),
                ('VelocidadGiro', 'float'), ('AlturaFlotar', 'float'), ('VelocidadFlotar', 'float'),
                ('ResolucionJitter', 'float'), ('Jitter', 'float'), ('InfladoSuave', 'float'),
                ('AlturaMin', 'float'), ('AlturaMax', 'float')],
               [('Posicion', 'float3'), ('NormalSalida', 'float3'), ('DireccionSalida', 'float3')])



def props_compartidas(G):
    """Propiedades de onda, glitch e ítem (mismas refs en los dos shaders)."""
    f = G.prop_float
    return {
        'amin': f('Altura Min', '_AlturaMin', -0.5),
        'amax': f('Altura Max', '_AlturaMax', 0.5),
        'vref': f('Velocidad Refresco', '_VelocidadRefresco', 0.6, -3, 3),
        'aref': f('Ancho Refresco', '_AnchoRefresco', 0.15, 0.01, 1),
        'aonda': f('Amplitud Onda', '_AmplitudOnda', 0.05, 0, 0.3),
        'ondu': f('Ondulacion', '_Ondulacion', 0.5, 0, 1),
        # 1 = inflar desde el centro (sin huecos en aristas duras), 0 = por la normal
        'suave': f('Inflado Suave', '_InfladoSuave', 1, 0, 1),
        'fgl': f('Franjas Glitch', '_FranjasGlitch', 16, 4, 64),
        'fpsgl': f('FPS Glitch', '_FPSGlitch', 10, 1, 30),
        'prgl': f('Probabilidad Glitch', '_ProbabilidadGlitch', 0.15, 0, 1),
        'fzgl': f('Fuerza Glitch', '_FuerzaGlitch', 0.05, 0, 0.3),
        'vgiro': f('Velocidad Giro', '_VelocidadGiro', 90, -360, 360),
        'aflot': f('Altura Flotar', '_AlturaFlotar', 0.1, 0, 0.5),
        'vflot': f('Velocidad Flotar', '_VelocidadFlotar', 2, 0, 10),
        'rjit': f('Resolucion Jitter', '_ResolucionJitter', 160, 32, 640),
        'jit': f('Jitter', '_Jitter', 1, 0, 1),
    }


def props_onda(pr):
    return [(pr['vref'], 'Velocidad'), (pr['aref'], 'Ancho'), (pr['amin'], 'AlturaMin'),
            (pr['amax'], 'AlturaMax'), (pr['ondu'], 'Ondulacion')]


def props_glitch(pr):
    return [(pr['fgl'], 'Franjas'), (pr['fpsgl'], 'FPS'), (pr['prgl'], 'Probabilidad')]


def cadena_vertices(G, pr, tiempo, titulo='1) Vértices: onda, glitch, giro/flotar y jitter PS1'):
    """Position/Normal (objeto) -> OndaRefresco -> GlitchFranjas -> VerticesRetro.
    Devuelve el nodo VerticesRetro (salidas Posicion y NormalSalida); la NormalSalida ya se
    conecta al bloque Normal, la Posicion la conecta quien llama."""
    N, A, P = G.nodo, G.arista, G.prop_nodo
    g1 = G.grupo(titulo, -3400, 1900)
    pos_os = N('PositionNode', -3350, 2000, extra={'m_Space': 0}, grupo=g1)        # objeto
    nor_os = N('NormalVectorNode', -3350, 2140, extra={'m_Space': 0}, grupo=g1)    # objeto

    onda_v = funcion(G, 'OndaRefresco', ONDA, *ONDA_IO, -2900, 2000, g1)
    A(pos_os, 0, onda_v, S(onda_v, 'PosOS'))
    A(tiempo, 0, onda_v, S(onda_v, 'Tiempo'))
    for i, (prop, nom) in enumerate(props_onda(pr)):
        A(P(prop, -3150, 2300 + 60 * i, grupo=g1), 0, onda_v, S(onda_v, nom))

    glitch_v = funcion(G, 'GlitchFranjas', GLITCH, *GLITCH_IO, -2600, 2200, g1)
    A(onda_v, S(onda_v, 'Altura'), glitch_v, S(glitch_v, 'Altura'))
    A(tiempo, 0, glitch_v, S(glitch_v, 'Tiempo'))
    for i, (prop, nom) in enumerate(props_glitch(pr)):
        A(P(prop, -2900, 2650 + 60 * i, grupo=g1), 0, glitch_v, S(glitch_v, nom))

    vert = funcion(G, 'VerticesRetro', VERTICES, *VERTICES_IO, -2200, 2000, g1)
    A(pos_os, 0, vert, S(vert, 'PosOS'))
    A(nor_os, 0, vert, S(vert, 'NormalOS'))
    A(onda_v, S(onda_v, 'Onda'), vert, S(vert, 'Onda'))
    A(glitch_v, S(glitch_v, 'Glitch'), vert, S(vert, 'Glitch'))
    A(tiempo, 0, vert, S(vert, 'Tiempo'))
    props_vert = [(pr['aonda'], 'AmplitudOnda'), (pr['fzgl'], 'FuerzaGlitch'), (pr['vgiro'], 'VelocidadGiro'),
                  (pr['aflot'], 'AlturaFlotar'), (pr['vflot'], 'VelocidadFlotar'),
                  (pr['rjit'], 'ResolucionJitter'), (pr['jit'], 'Jitter'),
                  (pr['suave'], 'InfladoSuave'), (pr['amin'], 'AlturaMin'), (pr['amax'], 'AlturaMax')]
    for i, (prop, nom) in enumerate(props_vert):
        A(P(prop, -2500, 2500 + 60 * i, grupo=g1), 0, vert, S(vert, nom))
    G.nota('Onda: la banda sube por el objeto entre Altura Min y Altura Max (espacio objeto; '
           'esfera/cubo de Unity = -0.5..0.5, cápsula = -1..1) y empuja los vértices hacia afuera. '
           'Inflado Suave = 1 empuja desde el centro (las esquinas repetidas de aristas duras se '
           'mueven juntas: sin huecos); 0 = por la normal. Ondulacion añade un anillo hacia dentro. '
           'Se ve mejor con mallas con suficientes vértices (esfera, modelo).',
           -3350, 2750, 460, 120, g1)
    G.nota('Jitter PS1: cada vértice se redondea a una rejilla de "Resolucion Jitter" píxeles '
           'verticales en pantalla y se regresa a espacio objeto. No se aplica en la sombra ni en la '
           'preview de Shader Graph.', -2500, 2950, 420, 90, g1)
    normal_block = next(o for o in G.objs if o.get('m_Name') == 'VertexDescription.Normal')
    A(vert, S(vert, 'NormalSalida'), normal_block, 0)
    return vert
