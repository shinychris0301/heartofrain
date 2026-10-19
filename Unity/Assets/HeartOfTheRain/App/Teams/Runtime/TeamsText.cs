using System;using System.Collections.Generic;using System.Globalization;using System.Text;
namespace HeartOfTheRain.App.Teams {
 public static class TeamsText {
  static readonly float[] Widths={0.27906f,0.26000f,0.48094f,0.60000f,0.60000f,0.95406f,0.74500f,0.25594f,0.38203f,0.38203f,0.45406f,0.60000f,0.26000f,0.44000f,0.26000f,0.33094f,0.60000f,0.60000f,0.60000f,0.60000f,0.60000f,0.60000f,0.60000f,0.60000f,0.60000f,0.60000f,0.26000f,0.26000f,0.60000f,0.60000f,0.60000f,0.46797f,0.95203f,0.75297f,0.69500f,0.68406f,0.77406f,0.60500f,0.57000f,0.74203f,0.78000f,0.29703f,0.37203f,0.68797f,0.57297f,0.87594f,0.75297f,0.79594f,0.66406f,0.79594f,0.69594f,0.64094f,0.63203f,0.74297f,0.72703f,1.12000f,0.68500f,0.63094f,0.61500f,0.37703f,0.33094f,0.37703f,0.60000f,0.50000f,0.38797f,0.55703f,0.61000f,0.47797f,0.61000f,0.54906f,0.38203f,0.61500f,0.59500f,0.26797f,0.27297f,0.55797f,0.33297f,0.88906f,0.59500f,0.58906f,0.61000f,0.61000f,0.41203f,0.49203f,0.40406f,0.59000f,0.53406f,0.86094f,0.55906f,0.53297f,0.48000f,0.41406f,0.30203f,0.41406f,0.60000f};
  public static string Limit(string value,int limit){var e=StringInfo.GetTextElementEnumerator(value??"");var b=new StringBuilder();int n=0;while(e.MoveNext()&&n++<limit)b.Append(e.GetTextElement());return b.ToString();}
  public static string Wrap(string value,float width,int size){
   var lines=new List<string>();foreach(var paragraph in (value??"").Replace("\r","").Split('\n')){
    string line="";float used=0;foreach(string word in paragraph.Split(' ')){
     float gap=line.Length>0?Widths[0]*size:0;float ww=Measure(word,size);
     if(line.Length>0&&used+gap+ww>width){lines.Add(line);line="";used=0;gap=0;}
     if(ww>width){if(line.Length>0){lines.Add(line);line="";used=0;}var it=StringInfo.GetTextElementEnumerator(word);while(it.MoveNext()){string t=it.GetTextElement();float tw=Measure(t,size);if(line.Length>0&&used+tw>width){lines.Add(line);line="";used=0;}line+=t;used+=tw;}}
     else{if(line.Length>0)line+=" ";line+=word;used+=gap+ww;}
    }lines.Add(line);
   }return string.Join("\n",lines);
  }
  static float Measure(string s,int size){float w=0;foreach(char c in s)w+=(c>=32&&c<=126?Widths[c-32]:1.1f)*size;return w;}
 }
}