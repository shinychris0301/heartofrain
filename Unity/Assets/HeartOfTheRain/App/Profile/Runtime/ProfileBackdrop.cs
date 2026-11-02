using UnityEngine;

namespace HeartOfTheRain.App.Profile
{
    // Six separable box passes avoid a synchronous GPU readback and CPU pixel filtering.
    internal static class ProfileBackdrop
    {
        public static RenderTexture Blur(Texture source)
        {
            if(!source)return null;
            var shader=Resources.Load<Shader>("HeartOfTheRainProfile/BackdropBlur");
            if(!shader||!shader.isSupported)return null;
            int w=256,h=Mathf.Clamp(Mathf.RoundToInt(w*source.height/(float)source.width),96,512);
            RenderTexture result=null,scratch=null;Material material=null;
            var previous=RenderTexture.active;
            try
            {
                result=new RenderTexture(w,h,0,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB){name="Profile chapter backdrop",filterMode=FilterMode.Bilinear,wrapMode=TextureWrapMode.Clamp};
                if(!result.Create())throw new System.InvalidOperationException("Backdrop render target unavailable");
                scratch=RenderTexture.GetTemporary(w,h,0,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB);scratch.filterMode=FilterMode.Bilinear;scratch.wrapMode=TextureWrapMode.Clamp;
                material=new Material(shader);Graphics.Blit(source,result);
                for(int pass=0;pass<3;pass++)
                {
                    material.SetVector("_Direction",new Vector4(1f/w,0,0,0));Graphics.Blit(result,scratch,material);
                    material.SetVector("_Direction",new Vector4(0,1f/h,0,0));Graphics.Blit(scratch,result,material);
                }
                return result;
            }
            catch(System.Exception e){Debug.LogWarning("Profile backdrop blur unavailable: "+e.Message);Release(result);return null;}
            finally{RenderTexture.active=previous;if(scratch)RenderTexture.ReleaseTemporary(scratch);if(material)Object.Destroy(material);}
        }
        public static void Release(RenderTexture texture){if(!texture)return;texture.Release();Object.Destroy(texture);}
    }
}
