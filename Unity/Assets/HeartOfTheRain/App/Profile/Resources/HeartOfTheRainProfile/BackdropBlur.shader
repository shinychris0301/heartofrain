Shader "Hidden/HeartOfTheRain/ProfileBackdrop"
{
    Properties { _MainTex("Source", 2D) = "white" {} }
    SubShader
    {
        Cull Off ZWrite Off ZTest Always
        Pass
        {
            CGPROGRAM
            #pragma vertex vert_img
            #pragma fragment frag
            #include "UnityCG.cginc"
            sampler2D _MainTex;
            float4 _Direction;
            fixed4 frag(v2f_img input) : SV_Target
            {
                float4 sum=0;
                [unroll] for(int offset=-4;offset<=4;offset++)sum+=tex2D(_MainTex,saturate(input.uv+_Direction.xy*offset));
                return sum/9;
            }
            ENDCG
        }
    }
    Fallback Off
}
