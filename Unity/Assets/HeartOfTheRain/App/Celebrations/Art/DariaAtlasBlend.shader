Shader "HeartOfTheRain/UI/DariaAtlasBlend"
{
 Properties {
  [PerRendererData] _MainTex ("Atlas",2D)="white" {}
  _Color ("Tint",Color)=(1,1,1,1)
  _FrameA ("Frame A",Vector)=(0,0,0.25,0.25)
  _FrameB ("Frame B",Vector)=(0,0,0.25,0.25)
  _Blend ("Blend",Range(0,1))=0
  _StencilComp ("Stencil Comparison",Float)=8
  _Stencil ("Stencil ID",Float)=0
  _StencilOp ("Stencil Operation",Float)=0
  _StencilWriteMask ("Stencil Write Mask",Float)=255
  _StencilReadMask ("Stencil Read Mask",Float)=255
  _ColorMask ("Color Mask",Float)=15
  [Toggle(UNITY_UI_ALPHACLIP)] _UseUIAlphaClip ("Alpha Clip",Float)=0
 }
 SubShader {
  Tags {"Queue"="Transparent" "IgnoreProjector"="True" "RenderType"="Transparent" "PreviewType"="Plane" "CanUseSpriteAtlas"="False"}
  Stencil {Ref [_Stencil] Comp [_StencilComp] Pass [_StencilOp] ReadMask [_StencilReadMask] WriteMask [_StencilWriteMask]}
  Cull Off Lighting Off ZWrite Off ZTest [unity_GUIZTestMode]
  Blend SrcAlpha OneMinusSrcAlpha ColorMask [_ColorMask]
  Pass {
   CGPROGRAM
   #pragma vertex vert
   #pragma fragment frag
   #pragma target 2.0
   #pragma multi_compile_local _ UNITY_UI_CLIP_RECT
   #pragma multi_compile_local _ UNITY_UI_ALPHACLIP
   #include "UnityCG.cginc"
   #include "UnityUI.cginc"
   struct appdata {float4 vertex:POSITION;fixed4 color:COLOR;float2 uv:TEXCOORD0;};
   struct v2f {float4 vertex:SV_POSITION;fixed4 color:COLOR;float2 uv:TEXCOORD0;float4 world:TEXCOORD1;};
   sampler2D _MainTex;fixed4 _Color;float4 _FrameA,_FrameB,_ClipRect;float _Blend;
   v2f vert(appdata v) {v2f o;o.world=v.vertex;o.vertex=UnityObjectToClipPos(v.vertex);o.uv=v.uv;o.color=v.color*_Color;return o;}
   fixed4 frag(v2f i):SV_Target {
    fixed4 a=tex2D(_MainTex,_FrameA.xy+i.uv*_FrameA.zw),b=tex2D(_MainTex,_FrameB.xy+i.uv*_FrameB.zw);
    float alpha=lerp(a.a,b.a,_Blend);
    fixed4 c=fixed4(lerp(a.rgb*a.a,b.rgb*b.a,_Blend)/max(alpha,.0001),alpha)*i.color;
    c.a*=smoothstep(0,.055,i.uv.y);
    #ifdef UNITY_UI_CLIP_RECT
    c.a*=UnityGet2DClipping(i.world.xy,_ClipRect);
    #endif
    #ifdef UNITY_UI_ALPHACLIP
    clip(c.a-.001);
    #endif
    return c;
   }
   ENDCG
  }
 }
}
