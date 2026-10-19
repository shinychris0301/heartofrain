Shader "HeartOfTheRain/M20/OrbTileGlow"
{
    Properties
    {
        [PerRendererData] _MainTex ("Sprite", 2D) = "white" {}
        [PerRendererData] _Glow ("Target Light", Range(0,1)) = 0
        _Color ("Tint", Color) = (1,1,1,1)
        [HideInInspector] _RendererColor ("Renderer Color", Color) = (1,1,1,1)
        [HideInInspector] _Flip ("Flip", Vector) = (1,1,1,1)
    }
    SubShader
    {
        Tags { "Queue"="Transparent" "RenderType"="Transparent" "IgnoreProjector"="True" "CanUseSpriteAtlas"="True" }
        Cull Off Lighting Off ZWrite Off
        Blend One OneMinusSrcAlpha
        Pass
        {
            Tags { "LightMode"="SRPDefaultUnlit" }
            CGPROGRAM
            #pragma vertex SpriteVert
            #pragma fragment OrbGlowFrag
            #pragma multi_compile_instancing
            #include "UnitySprites.cginc"
            float _Glow;
            float4 _MainTex_TexelSize;
            fixed4 OrbGlowFrag(v2f IN) : SV_Target
            {
                fixed4 c = SampleSpriteTexture(IN.texcoord) * IN.color;
                if (_Glow > 0)
                {
                    float2 uv = IN.texcoord, o = _MainTex_TexelSize.xy * 8;
                    float nearAlpha = 1;
                    nearAlpha = min(nearAlpha, SampleSpriteTexture(uv + float2(o.x,0)).a);
                    nearAlpha = min(nearAlpha, SampleSpriteTexture(uv - float2(o.x,0)).a);
                    nearAlpha = min(nearAlpha, SampleSpriteTexture(uv + float2(0,o.y)).a);
                    nearAlpha = min(nearAlpha, SampleSpriteTexture(uv - float2(0,o.y)).a);
                    nearAlpha = min(nearAlpha, SampleSpriteTexture(uv + o).a);
                    nearAlpha = min(nearAlpha, SampleSpriteTexture(uv - o).a);
                    nearAlpha = min(nearAlpha, SampleSpriteTexture(uv + float2(o.x,-o.y)).a);
                    nearAlpha = min(nearAlpha, SampleSpriteTexture(uv + float2(-o.x,o.y)).a);
                    float edge = saturate((SampleSpriteTexture(uv).a - nearAlpha) * 3);
                    c.rgb = lerp(c.rgb, fixed3(1.0,1.0,0.96), saturate(_Glow) * (.22 + .78 * edge));
                }
                c.rgb *= c.a;
                return c;
            }
            ENDCG
        }
    }
}
