// Toon + Borderlands + Dither (URP 17, Unity 6)
//
// - Toon: light is cut into flat bands instead of a gradient.
// - Dither: the border between bands is resolved with an on-screen Bayer pattern
//   (comic-style dot pattern) instead of a clean cut.
// - Borderlands: thick ink outline (inverted hull) + inner ink lines where the
//   surface turns away from the camera.
// - City transition: when _CityDissolve is on, every pass is dissolved with the same
//   Bayer pattern using the global _CityBlend (1 = fully visible, 0 = fully gone).
//   Used as an overlay on top of the original materials for a gradual crossfade.
Shader "Showcase/Test"
{
    Properties
    {
        [Header(Base)]
        [MainTexture] _BaseMap ("Textura", 2D) = "white" {}
        [MainColor] _BaseColor ("Color", Color) = (1, 1, 1, 1)

        [Header(Toon)]
        _ShadowColor ("Color de sombra", Color) = (0.28, 0.24, 0.38, 1)
        [IntRange] _Steps ("Bandas de luz", Range(1, 6)) = 2
        _AmbientStrength ("Luz ambiental", Range(0, 1)) = 0.35

        [Header(Dither)]
        _DitherAmount ("Dither entre bandas", Range(0, 1)) = 0.6
        _DitherScale ("Tamaño del punto (px)", Range(1, 8)) = 2

        [Header(Brillo especular)]
        [HDR] _SpecColor ("Color del brillo", Color) = (1, 1, 1, 1)
        _SpecSize ("Tamaño del brillo", Range(0, 1)) = 0.15
        _SpecIntensity ("Intensidad del brillo", Range(0, 1)) = 0

        [Header(Tinta Borderlands)]
        _OutlineColor ("Color de tinta", Color) = (0.02, 0.02, 0.03, 1)
        _OutlineWidth ("Grosor del contorno (px)", Range(0, 12)) = 4
        _InkThreshold ("Umbral de tinta interior", Range(0, 1)) = 0.78
        _InkStrength ("Fuerza de tinta interior", Range(0, 1)) = 0.6

        [Header(City Transition)]
        [Toggle] _CityDissolve ("Disolver con _CityBlend global", Float) = 0
        // Set by CityShaderTransition so the overlay wins the depth test against the original mesh
        [HideInInspector] _OffsetFactor ("Depth offset factor", Float) = 0
        [HideInInspector] _OffsetUnits ("Depth offset units", Float) = 0
    }

    SubShader
    {
        Tags
        {
            "RenderType" = "Opaque"
            "RenderPipeline" = "UniversalPipeline"
            "Queue" = "Geometry"
        }

        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        #include "../Common/ShowcaseCommon.hlsl"

        TEXTURE2D(_BaseMap);
        SAMPLER(sampler_BaseMap);

        CBUFFER_START(UnityPerMaterial)
            float4 _BaseMap_ST;
            half4 _BaseColor;
            half4 _ShadowColor;
            half4 _SpecColor;
            half4 _OutlineColor;
            float _Steps;
            float _AmbientStrength;
            float _DitherAmount;
            float _DitherScale;
            float _SpecSize;
            float _SpecIntensity;
            float _OutlineWidth;
            float _InkThreshold;
            float _InkStrength;
            float _CityDissolve;
        CBUFFER_END

        // Global, set from C# with Shader.SetGlobalFloat. Must live OUTSIDE the material CBUFFER.
        float _CityBlend;

        // Screen-door dissolve: discards pixels using the same Bayer pattern as the toon bands.
        // blend = 1 keeps every pixel, blend = 0 discards every pixel.
        void CityDissolveClip(float4 positionCS)
        {
            if (_CityDissolve > 0.5)
            {
                float threshold = DitherThreshold(positionCS.xy, _DitherScale);
                clip(_CityBlend * 1.02 - 0.01 - threshold);
            }
        }
        ENDHLSL

        // -------------------------------------------------------------------
        // Toon light with dither
        // -------------------------------------------------------------------
        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }

            Cull Back
            ZWrite On
            Offset [_OffsetFactor], [_OffsetUnits]

            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag

            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile _ _ADDITIONAL_LIGHTS
            #pragma multi_compile _ _CLUSTER_LIGHT_LOOP
            #pragma multi_compile_fragment _ _ADDITIONAL_LIGHT_SHADOWS
            #pragma multi_compile_fragment _ _SHADOWS_SOFT
            #pragma multi_compile_fog
            #pragma multi_compile_instancing

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
                float2 uv : TEXCOORD0;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float2 uv : TEXCOORD0;
                float3 positionWS : TEXCOORD1;
                float3 normalWS : TEXCOORD2;
                float fogFactor : TEXCOORD3;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            Varyings Vert(Attributes input)
            {
                Varyings output = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_TRANSFER_INSTANCE_ID(input, output);

                VertexPositionInputs positions = GetVertexPositionInputs(input.positionOS.xyz);
                output.positionCS = positions.positionCS;
                output.positionWS = positions.positionWS;
                output.normalWS = TransformObjectToWorldNormal(input.normalOS);
                output.uv = TRANSFORM_TEX(input.uv, _BaseMap);
                output.fogFactor = ComputeFogFactor(positions.positionCS.z);
                return output;
            }

            // Cuts the light into bands. 'jitter' (-0.5..0.5) shifts the cut
            // pixel by pixel, which turns the border into a dot pattern.
            half ToonBands(half lightAmount, half jitter)
            {
                half steps = max(_Steps, 1.0);
                return saturate(floor(lightAmount * steps + 0.5 + jitter * _DitherAmount) / steps);
            }

            half4 Frag(Varyings input) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(input);

                // Transition dissolve first, so discarded pixels skip all the lighting work
                CityDissolveClip(input.positionCS);

                half4 albedo = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, input.uv) * _BaseColor;
                half3 normalWS = normalize(input.normalWS);
                half3 viewDirWS = GetWorldSpaceNormalizeViewDir(input.positionWS);

                // The Forward+ additional light loop needs this data.
                InputData inputData = (InputData)0;
                inputData.positionWS = input.positionWS;
                inputData.normalWS = normalWS;
                inputData.viewDirectionWS = viewDirWS;
                inputData.normalizedScreenSpaceUV = GetNormalizedScreenSpaceUV(input.positionCS);

                half jitter = DitherThreshold(input.positionCS.xy, _DitherScale) - 0.5;

                // Main light
                float4 shadowCoord = TransformWorldToShadowCoord(input.positionWS);
                Light mainLight = GetMainLight(shadowCoord);
                half mainLit = saturate(dot(normalWS, mainLight.direction))
                    * mainLight.shadowAttenuation * mainLight.distanceAttenuation;
                half mainBand = ToonBands(mainLit, jitter);

                half3 shadowTint = lerp(_ShadowColor.rgb, half3(1.0, 1.0, 1.0), mainBand);
                half3 color = albedo.rgb * shadowTint * mainLight.color;

                // Flat specular highlight
                half3 halfDir = normalize(mainLight.direction + viewDirWS);
                half specTerm = pow(saturate(dot(normalWS, halfDir)), lerp(256.0, 8.0, _SpecSize));
                half specMask = step(0.5, specTerm + jitter * _DitherAmount * 0.5) * mainBand;
                color += _SpecColor.rgb * mainLight.color * specMask * _SpecIntensity;

                // Additional lights (also banded)
                #if defined(_ADDITIONAL_LIGHTS)
                uint lightCount = GetAdditionalLightsCount();
                LIGHT_LOOP_BEGIN(lightCount)
                    Light light = GetAdditionalLight(lightIndex, input.positionWS, half4(1.0, 1.0, 1.0, 1.0));
                    half lightAmount = saturate(dot(normalWS, light.direction))
                        * light.shadowAttenuation * light.distanceAttenuation;
                    color += albedo.rgb * light.color * ToonBands(lightAmount, jitter);
                LIGHT_LOOP_END
                #endif

                // Ambient
                color += albedo.rgb * SampleSH(normalWS) * _AmbientStrength;

                // Inner ink: darkens where the surface turns away from the camera.
                half fresnel = 1.0 - saturate(dot(normalWS, viewDirWS));
                half ink = step(_InkThreshold, fresnel + jitter * _DitherAmount * 0.2);
                color = lerp(color, _OutlineColor.rgb, ink * _InkStrength);

                color = MixFog(color, input.fogFactor);
                return half4(color, 1.0);
            }
            ENDHLSL
        }

        // -------------------------------------------------------------------
        // Outline: back faces inflated along the normal
        // -------------------------------------------------------------------
        Pass
        {
            Name "Outline"
            Tags { "LightMode" = "SRPDefaultUnlit" }

            Cull Front
            ZWrite On

            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile_fog
            #pragma multi_compile_instancing

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float fogFactor : TEXCOORD0;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            Varyings Vert(Attributes input)
            {
                Varyings output = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_TRANSFER_INSTANCE_ID(input, output);

                float4 positionCS = TransformObjectToHClip(input.positionOS.xyz);
                float3 normalWS = TransformObjectToWorldNormal(input.normalOS);
                float3 normalCS = TransformWorldToHClipDir(normalWS);

                // Constant thickness in pixels, regardless of distance.
                float2 direction = normalCS.xy / max(length(normalCS.xy), 1e-5);
                positionCS.xy += direction * (_OutlineWidth * 2.0 / _ScreenParams.xy) * positionCS.w;

                output.positionCS = positionCS;
                output.fogFactor = ComputeFogFactor(positionCS.z);
                return output;
            }

            half4 Frag(Varyings input) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(input);
                CityDissolveClip(input.positionCS);

                half3 color = MixFog(_OutlineColor.rgb, input.fogFactor);
                return half4(color, 1.0);
            }
            ENDHLSL
        }

        // -------------------------------------------------------------------
        // Shadows
        // -------------------------------------------------------------------
        Pass
        {
            Name "ShadowCaster"
            Tags { "LightMode" = "ShadowCaster" }

            ZWrite On
            ZTest LEqual
            ColorMask 0
            Cull Back

            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile_instancing
            #pragma multi_compile_vertex _ _CASTING_PUNCTUAL_LIGHT_SHADOW

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Shadows.hlsl"

            float3 _LightDirection;
            float3 _LightPosition;

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            Varyings Vert(Attributes input)
            {
                Varyings output = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_TRANSFER_INSTANCE_ID(input, output);

                float3 positionWS = TransformObjectToWorld(input.positionOS.xyz);
                float3 normalWS = TransformObjectToWorldNormal(input.normalOS);

                #if defined(_CASTING_PUNCTUAL_LIGHT_SHADOW)
                float3 lightDirectionWS = normalize(_LightPosition - positionWS);
                #else
                float3 lightDirectionWS = _LightDirection;
                #endif

                float4 positionCS = TransformWorldToHClip(ApplyShadowBias(positionWS, normalWS, lightDirectionWS));
                output.positionCS = ApplyShadowClamping(positionCS);
                return output;
            }

            half4 Frag(Varyings input) : SV_Target
            {
                return 0;
            }
            ENDHLSL
        }

        // -------------------------------------------------------------------
        // Depth
        // -------------------------------------------------------------------
        Pass
        {
            Name "DepthOnly"
            Tags { "LightMode" = "DepthOnly" }

            ZWrite On
            ColorMask R
            Cull Back

            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile_instancing

            struct Attributes
            {
                float4 positionOS : POSITION;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            Varyings Vert(Attributes input)
            {
                Varyings output = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_TRANSFER_INSTANCE_ID(input, output);
                output.positionCS = TransformObjectToHClip(input.positionOS.xyz);
                return output;
            }

            half4 Frag(Varyings input) : SV_Target
            {
                CityDissolveClip(input.positionCS);
                return input.positionCS.z;
            }
            ENDHLSL
        }

        // -------------------------------------------------------------------
        // Depth + normals (used by SSAO and other screen effects)
        // -------------------------------------------------------------------
        Pass
        {
            Name "DepthNormals"
            Tags { "LightMode" = "DepthNormals" }

            ZWrite On
            Cull Back

            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile_instancing

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 normalWS : TEXCOORD0;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            Varyings Vert(Attributes input)
            {
                Varyings output = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_TRANSFER_INSTANCE_ID(input, output);
                output.positionCS = TransformObjectToHClip(input.positionOS.xyz);
                output.normalWS = TransformObjectToWorldNormal(input.normalOS);
                return output;
            }

            half4 Frag(Varyings input) : SV_Target
            {
                CityDissolveClip(input.positionCS);
                return half4(normalize(input.normalWS), 0.0);
            }
            ENDHLSL
        }
    }

    FallBack "Hidden/Universal Render Pipeline/FallbackError"
}
