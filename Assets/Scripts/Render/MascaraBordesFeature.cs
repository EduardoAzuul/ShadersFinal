using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;
using UnityEngine.Rendering.RenderGraphModule;
using UnityEngine.Rendering.Universal;

/// <summary>
/// Dibuja todos los objetos opacos en una textura "_MascaraBordes" usando el shader MascaraBordes
/// como override: cada objeto escribe el valor "_ColorBordes" de SU PROPIO material.
/// El efecto de pantalla BordesBorderlands lee esa máscara: solo dibuja líneas donde alfa > 0
/// y con ese color. Así cada material decide si lleva líneas y de qué color.
/// </summary>
public class MascaraBordesFeature : ScriptableRendererFeature
{
    [Tooltip("Shader 'Hidden/Proyecto Final/MascaraBordes'")]
    public Shader shaderMascara;

    [Tooltip("Capas que pueden llevar líneas")]
    public LayerMask capas = ~0;

    public RenderPassEvent evento = RenderPassEvent.AfterRenderingOpaques;

    PasoMascara paso;

    public override void Create()
    {
        paso = new PasoMascara { renderPassEvent = evento };
    }

    public override void AddRenderPasses(ScriptableRenderer renderer, ref RenderingData renderingData)
    {
        if (shaderMascara == null) return;
        paso.shader = shaderMascara;
        paso.capas = capas;
        paso.renderPassEvent = evento;
        renderer.EnqueuePass(paso);
    }

    protected override void Dispose(bool disposing)
    {
        paso?.Liberar();
    }

    class PasoMascara : ScriptableRenderPass
    {
        public Shader shader;
        public LayerMask capas;

        static readonly int IdMascara = Shader.PropertyToID("_MascaraBordes");
        static readonly List<ShaderTagId> Etiquetas = new List<ShaderTagId>
        {
            new ShaderTagId("UniversalForward"),
            new ShaderTagId("UniversalForwardOnly"),
            new ShaderTagId("SRPDefaultUnlit"),
        };

        RTHandle mascara;   // textura persistente (no la recicla el render graph)

        class Datos
        {
            public RendererListHandle lista;
        }

        public void Liberar()
        {
            mascara?.Release();
            mascara = null;
        }

        public override void RecordRenderGraph(RenderGraph renderGraph, ContextContainer frameData)
        {
            var recursos = frameData.Get<UniversalResourceData>();
            var camara = frameData.Get<UniversalCameraData>();
            var render = frameData.Get<UniversalRenderingData>();
            var luces = frameData.Get<UniversalLightData>();

            var desc = camara.cameraTargetDescriptor;
            desc.graphicsFormat = GraphicsFormat.R8G8B8A8_UNorm;
            desc.depthStencilFormat = GraphicsFormat.None;
            RenderingUtils.ReAllocateHandleIfNeeded(ref mascara, desc, FilterMode.Point,
                TextureWrapMode.Clamp, name: "_MascaraBordes");
            TextureHandle destino = renderGraph.ImportTexture(mascara);

            var dibujo = RenderingUtils.CreateDrawingSettings(Etiquetas, render, camara, luces,
                camara.defaultOpaqueSortFlags);
            dibujo.overrideShader = shader;          // conserva las propiedades del material original
            dibujo.overrideShaderPassIndex = 0;
            var filtro = new FilteringSettings(RenderQueueRange.opaque, capas);

            using (var builder = renderGraph.AddRasterRenderPass<Datos>("Mascara Bordes", out var datos))
            {
                datos.lista = renderGraph.CreateRendererList(new RendererListParams(render.cullResults, dibujo, filtro));
                builder.UseRendererList(datos.lista);
                builder.SetRenderAttachment(destino, 0, AccessFlags.Write);
                builder.SetRenderAttachmentDepth(recursos.activeDepthTexture, AccessFlags.Read);
                builder.AllowPassCulling(false);
                builder.SetRenderFunc((Datos d, RasterGraphContext ctx) =>
                {
                    ctx.cmd.ClearRenderTarget(false, true, Color.clear);
                    ctx.cmd.DrawRendererList(d.lista);
                });
            }

            Shader.SetGlobalTexture(IdMascara, mascara);
        }
    }
}
