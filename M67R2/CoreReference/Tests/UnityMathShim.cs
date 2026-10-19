// HEADLESS TESTS ONLY. Not shipped in Unity/Assets. No renderer/input mocks.
using System;
namespace UnityEngine {
 public struct Vector2Int {
  public int x,y;public Vector2Int(int x,int y){this.x=x;this.y=y;}public int sqrMagnitude=>x*x+y*y;
  public static Vector2Int zero=>new Vector2Int(0,0);public static Vector2Int left=>new Vector2Int(-1,0);public static Vector2Int right=>new Vector2Int(1,0);public static Vector2Int up=>new Vector2Int(0,1);public static Vector2Int down=>new Vector2Int(0,-1);
  public static Vector2Int operator +(Vector2Int a,Vector2Int b)=>new Vector2Int(a.x+b.x,a.y+b.y);public static Vector2Int operator -(Vector2Int a,Vector2Int b)=>new Vector2Int(a.x-b.x,a.y-b.y);
  public static bool operator ==(Vector2Int a,Vector2Int b)=>a.x==b.x&&a.y==b.y;public static bool operator !=(Vector2Int a,Vector2Int b)=>!(a==b);public override bool Equals(object o)=>o is Vector2Int v&&v==this;public override int GetHashCode()=>x*397^y;
  public static implicit operator Vector2(Vector2Int a)=>new Vector2(a.x,a.y);
 }
 public struct Vector2 {
  public float x,y;public Vector2(float x,float y){this.x=x;this.y=y;}
  public static Vector2 operator +(Vector2 a,Vector2 b)=>new Vector2(a.x+b.x,a.y+b.y);public static Vector2 operator -(Vector2 a,Vector2 b)=>new Vector2(a.x-b.x,a.y-b.y);
  public static Vector2 operator *(Vector2 a,float b)=>new Vector2(a.x*b,a.y*b);public static Vector2 operator *(float b,Vector2 a)=>a*b;public static Vector2 operator /(Vector2 a,float b)=>new Vector2(a.x/b,a.y/b);
  public static float Distance(Vector2 a,Vector2 b)=>Mathf.Sqrt((a.x-b.x)*(a.x-b.x)+(a.y-b.y)*(a.y-b.y));
 }
 public struct Vector3 {public float x,y,z;public Vector3(float x,float y,float z){this.x=x;this.y=y;this.z=z;}}
 public static class Mathf {
  public const float PI=(float)Math.PI,Deg2Rad=PI/180,Rad2Deg=180/PI;
  public static int Min(int a,int b)=>Math.Min(a,b);public static float Min(float a,float b)=>Math.Min(a,b);public static int Max(int a,int b)=>Math.Max(a,b);public static float Max(float a,float b)=>Math.Max(a,b);
  public static int Clamp(int v,int a,int b)=>Math.Max(a,Math.Min(v,b));public static float Clamp(float v,float a,float b)=>Math.Max(a,Math.Min(v,b));public static float Clamp01(float v)=>Clamp(v,0,1);
  public static int Abs(int x)=>Math.Abs(x);public static float Abs(float x)=>Math.Abs(x);public static float Sqrt(float x)=>(float)Math.Sqrt(x);public static float Sin(float x)=>(float)Math.Sin(x);public static float Cos(float x)=>(float)Math.Cos(x);public static float Exp(float x)=>(float)Math.Exp(x);public static float Pow(float x,float y)=>(float)Math.Pow(x,y);public static float Atan2(float x,float y)=>(float)Math.Atan2(x,y);
  public static float Ceil(float x)=>(float)Math.Ceiling(x);public static int CeilToInt(float x)=>(int)Math.Ceiling(x);public static int FloorToInt(float x)=>(int)Math.Floor(x);public static int RoundToInt(float x)=>(int)Math.Round(x);
  public static float Lerp(float a,float b,float t)=>a+(b-a)*Clamp01(t);public static float SmoothStep(float a,float b,float t){t=Clamp01(t);return a+(b-a)*t*t*(3-2*t);}
 }
}
