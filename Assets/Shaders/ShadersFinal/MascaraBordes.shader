// Shader de utilidad para MascaraBordesFeature (no se asigna a materiales).
// Se usa como "override shader": dibuja cada objeto con el valor _ColorBordes de SU material.
// Alfa 0 (o un material sin esa propiedad) = el objeto no lleva líneas Borderlands.
Shader "Hidden/Proyecto Final/MascaraBordes"
{
    Properties
    {
        _ColorBordes ("Color Bordes", Color) = (0, 0, 0, 0)
    }
    SubShader
    {
        Tags { "RenderPipeline" = "UniversalPipeline" "RenderType" = "Opaque" }
        Pass
        {
            Name "Mascara"
            ZWrite Off
            ZTest LEqual
            Cull Back
            Offset -1, -1

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            // Fuera del CBUFFER a propósito: así se lee el valor del material original
            // aunque su CBUFFER (SRP Batcher) tenga otra estructura.
            float4 _ColorBordes;

            struct Entrada { float4 posicionOS : POSITION; };
            struct Salida  { float4 posicionCS : SV_POSITION; };

            Salida vert(Entrada e)
            {
                Salida s;
                s.posicionCS = TransformObjectToHClip(e.posicionOS.xyz);
                return s;
            }

            half4 frag(Salida s) : SV_Target
            {
                return _ColorBordes;
            }
            ENDHLSL
        }
    }
}
