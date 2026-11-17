#!/usr/bin/env python3
"""Genera Assets/Shaders/Blueprint.shadergraph: estilo blueprint.
Fondo azul + cuadrícula blanca pegada al objeto (triplanar, principal + subdivisiones)
+ tiza: dithering ordenado (Bayer) blanco en las sombras + contorno blanco por fresnel
+ decoraciones al azar (círculos, cruces, cotas, diagonales)."""
import os
from sg_comun import Grafo, PROYECTO, v2, v4

G = Grafo('Proyecto Final', con_textura=False)
N, A, P = G.nodo, G.arista, G.prop_nodo


def escalar(valor):
    return {**{f'e{i}{j}': 0.0 for i in range(4) for j in range(4)},
            'e00': valor, 'e01': valor, 'e02': valor, 'e03': valor}


# ------------------------------------------------------------------ propiedades
G.prop_color.update({'m_Name': 'Color Fondo', 'm_RefNameGeneratedByDisplayName': 'Color Fondo',
                     'm_Value': {'r': 0.15, 'g': 0.3, 'b': 0.68, 'a': 1.0}})
p_lin = G.prop_color_nueva('Color Lineas', '_ColorLineas', (0.92, 0.95, 1, 1))
p_dens = G.prop_float('Densidad Cuadricula', '_DensidadCuadricula', 4, 0.5, 40)
p_gros = G.prop_float('Grosor Cuadricula', '_GrosorCuadricula', 0.015, 0.001, 0.1)
p_sub = G.prop_float('Subdivisiones', '_Subdivisiones', 4, 1, 10)
p_osub = G.prop_float('Opacidad Subdivisiones', '_OpacidadSubdivisiones', 0.3, 0, 1)
p_nit = G.prop_float('Nitidez Triplanar', '_NitidezTriplanar', 8, 1, 32)
p_tdit = G.prop_float('Tamano Dither', '_TamanoDither', 2, 1, 8)
p_idit = G.prop_float('Intensidad Dither', '_IntensidadDither', 0.8, 0, 1)
p_usom = G.prop_float('Umbral Sombra', '_UmbralSombra', 0.35, 0, 1)
p_cont = G.prop_float('Grosor Contorno', '_GrosorContorno', 0.25, 0, 1)
# Líneas Borderlands de este material (las lee MascaraBordesFeature). Alfa 0 = sin líneas.
p_bordes = G.prop_color_nueva('Color Bordes', '_ColorBordes', (0.92, 0.95, 1, 1))
p_prob = G.prop_float('Cantidad Decoraciones', '_CantidadDecoraciones', 0.35, 0, 1)
p_odec = G.prop_float('Opacidad Decoraciones', '_OpacidadDecoraciones', 0.85, 0, 1)
p_semi = G.prop_float('Semilla', '_Semilla', 0)

# ================= 1) Coordenadas pegadas al objeto (triplanar) ===============
g1 = G.grupo('1) Coordenadas del objeto (triplanar)', -3400, -700)
pos_os = N('PositionNode', -3350, -600, extra={'m_Space': 0}, grupo=g1)        # objeto
obj = N('ObjectNode', -3350, -470, grupo=g1)
pos_sc = N('MultiplyNode', -3150, -600, grupo=g1)                              # × escala del objeto
A(pos_os, 0, pos_sc, 0)
A(obj, 1, pos_sc, 1)

nor_os = N('NormalVectorNode', -3350, -300, extra={'m_Space': 0}, grupo=g1)
abs_n = N('AbsoluteNode', -3150, -300, grupo=g1)
p_nit_n = P(p_nit, -3150, -180, grupo=g1)
pow_n = N('PowerNode', -2950, -300, grupo=g1)
pesos = N('SplitNode', -2750, -300, grupo=g1)                                  # peso de cada eje
s1 = N('AddNode', -2550, -350, grupo=g1)
suma = N('AddNode', -2350, -320, grupo=g1)                                     # suma de pesos
A(nor_os, 0, abs_n, 0)
A(abs_n, 1, pow_n, 0)
A(p_nit_n, 0, pow_n, 1)
A(pow_n, 2, pesos, 0)
A(pesos, 1, s1, 0)
A(pesos, 2, s1, 1)
A(s1, 2, suma, 0)
A(pesos, 3, suma, 1)
G.nota('La cuadrícula se proyecta desde los 3 ejes del objeto y se elige según hacia dónde mira '
       'cada cara (|normal|^Nitidez). Se multiplica por la escala del objeto para que las celdas '
       'no se estiren al escalarlo.', -3350, -60, 440, 90, g1)


def lineas_triplanar(densidad, x, y, grupo):
    """Distancia (0..0.5) a la línea más cercana de la cuadrícula, mezclada entre los 3 planos."""
    m = N('MultiplyNode', x, y, grupo=grupo)
    A(pos_sc, 2, m, 0)
    A(densidad[0], densidad[1], m, 1)
    fr = N('FractionNode', x + 200, y, grupo=grupo)
    om = N('OneMinusNode', x + 400, y + 80, grupo=grupo)
    mn = N('MinimumNode', x + 600, y, grupo=grupo)                             # min(f, 1-f) por eje
    spl = N('SplitNode', x + 800, y, grupo=grupo)
    A(m, 2, fr, 0)
    A(fr, 1, om, 0)
    A(fr, 1, mn, 0)
    A(om, 1, mn, 1)
    A(mn, 2, spl, 0)
    # plano YZ (mira a X) usa min(y,z); XZ usa min(x,z); XY usa min(x,y)
    acum = None
    for i, (a, b) in enumerate(((2, 3), (1, 3), (1, 2))):
        mi = N('MinimumNode', x + 1000, y - 100 + i * 110, grupo=grupo)
        A(spl, a, mi, 0)
        A(spl, b, mi, 1)
        pw = N('MultiplyNode', x + 1200, y - 100 + i * 110, grupo=grupo)
        A(mi, 2, pw, 0)
        A(pesos, i + 1, pw, 1)
        if acum is None:
            acum = pw
        else:
            ad = N('AddNode', x + 1400, y - 50 + i * 110, grupo=grupo)
            A(acum, 2, ad, 0)
            A(pw, 2, ad, 1)
            acum = ad
    dv = N('DivideNode', x + 1600, y, grupo=grupo)
    A(acum, 2, dv, 0)
    A(suma, 2, dv, 1)
    return dv


def a_mascara(dist, grosor, x, y, grupo):
    """1 - smoothstep(grosor, grosor·1.6, distancia): línea con borde suave."""
    e2 = N('MultiplyNode', x, y + 120, valores={1: escalar(1.6)}, grupo=grupo)
    ss = N('SmoothstepNode', x + 200, y, grupo=grupo)
    om = N('OneMinusNode', x + 400, y, grupo=grupo)
    A(grosor[0], grosor[1], ss, 0)
    A(grosor[0], grosor[1], e2, 0)
    A(e2, 2, ss, 1)
    A(dist, 2, ss, 2)
    A(ss, 3, om, 0)
    return om


# ================= 2) Cuadrícula ==============================================
g2 = G.grupo('2) Cuadrícula pegada al objeto: principal + subdivisiones', -2200, -900)
p_dens_n = P(p_dens, -2150, -800, grupo=g2)
p_gros_n = P(p_gros, -2150, -680, grupo=g2)
p_sub_n = P(p_sub, -2150, -560, grupo=g2)
d_main = lineas_triplanar((p_dens_n, 0), -1900, -850, g2)
m_main = a_mascara(d_main, (p_gros_n, 0), -150, -850, g2)
dens_sub = N('MultiplyNode', -1950, -560, grupo=g2)
A(p_dens_n, 0, dens_sub, 0)
A(p_sub_n, 0, dens_sub, 1)
d_sub = lineas_triplanar((dens_sub, 2), -1900, -400, g2)
gros_sub = N('MultiplyNode', -350, -280, grupo=g2)                             # mismo grosor real
A(p_gros_n, 0, gros_sub, 0)
A(p_sub_n, 0, gros_sub, 1)
m_sub0 = a_mascara(d_sub, (gros_sub, 2), -150, -400, g2)
p_osub_n = P(p_osub, 250, -280, grupo=g2)
m_sub = N('MultiplyNode', 450, -400, grupo=g2)
cuad = N('MaximumNode', 650, -600, grupo=g2)
A(m_sub0, 1, m_sub, 0)
A(p_osub_n, 0, m_sub, 1)
A(m_main, 1, cuad, 0)
A(m_sub, 2, cuad, 1)

# ================= 3) Tiza: dithering en las sombras ==========================
g3 = G.grupo('3) Tiza: dithering ordenado en la sombra', -2200, 150)
normal = N('NormalVectorNode', -2150, 250, grupo=g3)
luz = N('MainLightDirectionNode', -2150, 380, grupo=g3)
dot = N('DotProductNode', -1950, 300, grupo=g3)
remap = N('RemapNode', -1750, 300, valores={1: v2(-1, 1), 2: v2(1, 0)}, grupo=g3)   # Half-Lambert: 1 = luz
sombra = N('OneMinusNode', -1550, 300, grupo=g3)                              # 1 = sombra
p_usom_n = P(p_usom, -1550, 450, grupo=g3)
s_u = N('SubtractNode', -1350, 300, grupo=g3)
om_u = N('OneMinusNode', -1350, 450, grupo=g3)
d_u = N('DivideNode', -1150, 300, grupo=g3)
sat_u = N('SaturateNode', -950, 300, grupo=g3)                                # 0 bajo el umbral → 1
p_idit_n = P(p_idit, -950, 450, grupo=g3)
cant = N('MultiplyNode', -750, 300, grupo=g3)                                 # cantidad de tiza
sp = N('ScreenPositionNode', -1150, 600, grupo=g3)
p_tdit_n = P(p_tdit, -1150, 750, grupo=g3)
sp_d = N('DivideNode', -950, 650, grupo=g3)                                   # patrón más grande
dith = N('DitherNode', -550, 400, grupo=g3)
m_d = N('MultiplyNode', -350, 400, valores={1: escalar(1000)}, grupo=g3)
tiza = N('SaturateNode', -150, 400, grupo=g3)
A(normal, 0, dot, 0)
A(luz, 0, dot, 1)
A(dot, 2, remap, 0)
A(remap, 3, sombra, 0)
A(sombra, 1, s_u, 0)
A(p_usom_n, 0, s_u, 1)
A(p_usom_n, 0, om_u, 0)
A(s_u, 2, d_u, 0)
A(om_u, 1, d_u, 1)
A(d_u, 2, sat_u, 0)
A(sat_u, 1, cant, 0)
A(p_idit_n, 0, cant, 1)
A(sp, 0, sp_d, 0)
A(p_tdit_n, 0, sp_d, 1)
A(cant, 2, dith, 0)
A(sp_d, 2, dith, 1)
A(dith, 2, m_d, 0)
A(m_d, 2, tiza, 0)
G.nota('Dither (Bayer 4×4): pinta blanco en la fracción de píxeles que pide la cantidad de '
       'sombra, con un patrón ordenado. Dividir la posición de pantalla entre Tamano Dither '
       'agranda los "píxeles" del patrón. Bajo Umbral Sombra no hay tiza.',
       -2150, 850, 460, 100, g3)

# ================= 4) Contorno ===============================================
g4 = G.grupo('4) Contorno blanco (fresnel)', -2200, 1100)
view = N('ViewDirectionNode', -2150, 1200, grupo=g4)
dot_v = N('DotProductNode', -1950, 1200, grupo=g4)
sat_v = N('SaturateNode', -1750, 1200, grupo=g4)
p_cont_n = P(p_cont, -1750, 1350, grupo=g4)
e2 = N('AddNode', -1550, 1350, valores={1: v4(0.05)}, grupo=g4)
ss_c = N('SmoothstepNode', -1350, 1200, grupo=g4)
contorno = N('OneMinusNode', -1150, 1200, grupo=g4)
A(normal, 0, dot_v, 0)
A(view, 0, dot_v, 1)
A(dot_v, 2, sat_v, 0)
A(p_cont_n, 0, ss_c, 0)
A(p_cont_n, 0, e2, 0)
A(e2, 2, ss_c, 1)
A(sat_v, 1, ss_c, 2)
A(ss_c, 3, contorno, 0)


# ================= 5) Decoraciones al azar ====================================
CUERPO = r"""// Dibuja en algunas celdas de la cuadrícula (al azar) un elemento de plano técnico:
// círculo de construcción, cruz de centro, cota (línea con topes) o diagonal.
float3 w = Pesos / max(Pesos.x + Pesos.y + Pesos.z, 1e-4);
float3 p = PosObj * Densidad;
float total = 0;
[unroll] for (int k = 0; k < 3; k++)
{
    float2 q = (k == 0) ? p.yz : ((k == 1) ? p.xz : p.xy);
    float2 celda = floor(q) + Semilla * 17.0 + k * 31.0;
    float2 l = frac(q) - 0.5;                       // -0.5..0.5 dentro de la celda
    // número aleatorio por celda (hash)
    float2 h = frac(celda * float2(123.34, 456.21));
    h += dot(h, h + 45.32);
    float r = frac(h.x * h.y);
    float r2 = frac(r * 91.7 + 0.13);
    float g = Grosor;
    float m = 0;
    if (r < Cantidad * 0.35)            // círculo de construcción
    {
        float radio = lerp(0.15, 0.42, r2);
        m = 1 - smoothstep(g, g * 1.6, abs(length(l) - radio));
    }
    else if (r < Cantidad * 0.6)        // cruz de centro
    {
        float bx = max(abs(l.x) / g, abs(l.y) / 0.15);
        float by = max(abs(l.y) / g, abs(l.x) / 0.15);
        m = 1 - smoothstep(1, 1.6, min(bx, by));
    }
    else if (r < Cantidad * 0.85)       // cota: línea horizontal con topes
    {
        float y0 = (r2 - 0.5) * 0.6;
        float linea = max(abs(l.y - y0) / g, abs(l.x) / 0.4);
        float topes = max(abs(abs(l.x) - 0.4) / g, abs(l.y - y0) / 0.1);
        m = 1 - smoothstep(1, 1.6, min(linea, topes));
    }
    else if (r < Cantidad)              // diagonal
    {
        float d = abs(l.x - l.y * (r2 > 0.5 ? 1.0 : -1.0)) * 0.7071;
        m = (1 - smoothstep(g, g * 1.6, d)) * step(max(abs(l.x), abs(l.y)), 0.45);
    }
    total += m * w[k];
}
Out = saturate(total) * Opacidad;"""
g6 = G.grupo('5) Decoraciones al azar (Custom Function)', 300, 300)
deco = G.funcion('Decoraciones', CUERPO,
                 [('PosObj', 'float3'), ('Pesos', 'float3'), ('Densidad', 'float'), ('Grosor', 'float'),
                  ('Cantidad', 'float'), ('Opacidad', 'float'), ('Semilla', 'float')],
                 [('Out', 'float')], 600, 400, g6)
p_prob_n = P(p_prob, 350, 500, grupo=g6)
p_odec_n = P(p_odec, 350, 600, grupo=g6)
p_semi_n = P(p_semi, 350, 700, grupo=g6)
p_dens_n2 = P(p_dens, 350, 380, grupo=g6)
p_gros_n2 = P(p_gros, 350, 440, grupo=g6)
A(pos_sc, 2, deco, 0)
A(pow_n, 2, deco, 1)
A(p_dens_n2, 0, deco, 2)
A(p_gros_n2, 0, deco, 3)
A(p_prob_n, 0, deco, 4)
A(p_odec_n, 0, deco, 5)
A(p_semi_n, 0, deco, 6)
G.nota('En cada celda de la cuadrícula principal se tira un número al azar (hash de la celda). '
       'Según el número se dibuja un círculo, una cruz, una cota o una diagonal, o nada. '
       'Cambia Semilla para otra distribución.', 350, 800, 440, 90, g6)

# ================= 6) Componer ===============================================
g5 = G.grupo('6) Color final', 900, -200)
mx1 = N('MaximumNode', 950, -100, grupo=g5)
mx2 = N('MaximumNode', 1150, 0, grupo=g5)
p_fondo_n = P(G.prop_color, 1150, -250, grupo=g5)
p_lin_n = P(p_lin, 1150, 150, grupo=g5)
mezcla = N('LerpNode', 1350, -100, grupo=g5)
A(cuad, 2, mx1, 0)
A(tiza, 1, mx1, 1)
A(mx1, 2, mx2, 0)
A(contorno, 1, mx2, 1)
mx3 = N('MaximumNode', 1250, 50, grupo=g5)
A(mx2, 2, mx3, 0)
A(deco, 7, mx3, 1)
A(p_fondo_n, 0, mezcla, 0)
A(p_lin_n, 0, mezcla, 1)
A(mx3, 2, mezcla, 2)
A(mezcla, 3, G.base_color, 0)

G.guardar(os.path.join(PROYECTO, 'Assets/Shaders/Blueprint.shadergraph'))
