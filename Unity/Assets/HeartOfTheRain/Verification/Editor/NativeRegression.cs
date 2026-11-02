#if UNITY_EDITOR
using System;
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace HeartOfTheRain.Verification
{
    [InitializeOnLoad]
    public static class NativeRegression
    {
        const string Key="HOTR.NativeRegression";
        static NativeRegression(){if(SessionState.GetBool(Key,false))EditorApplication.update+=Tick;}
        public static void Run()
        {
            SessionState.SetBool(Key,true);SessionState.SetFloat(Key+".start",(float)EditorApplication.timeSinceStartup);
            EditorSceneManager.OpenScene("Assets/HeartOfTheRain/App/FirstStart/Scenes/M65_First_Start.unity");
            SetPortraitView();
            Directory.CreateDirectory(Application.persistentDataPath);
            File.WriteAllText(Path.Combine(Application.persistentDataPath,PlayerRegressionSuite.RequestFile),"opt-in native regression");
            EditorApplication.isPlaying=true;
        }
        static void SetPortraitView()
        {
            var assembly=typeof(Editor).Assembly;
            var sizes=assembly.GetType("UnityEditor.GameViewSizes");
            var singleton=typeof(ScriptableSingleton<>).MakeGenericType(sizes).GetProperty("instance",BindingFlags.Public|BindingFlags.Static).GetValue(null);
            var groupType=assembly.GetType("UnityEditor.GameViewSizeGroupType");
            var group=sizes.GetMethod("GetGroup").Invoke(singleton,new[]{Enum.Parse(groupType,"Standalone")});
            var sizeType=assembly.GetType("UnityEditor.GameViewSizeType");var viewSize=assembly.GetType("UnityEditor.GameViewSize");
            var size=Activator.CreateInstance(viewSize,BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance,null,new object[]{Enum.Parse(sizeType,"FixedResolution"),900,1600,"HOTR regression portrait"},null);
            int count=(int)group.GetType().GetMethod("GetTotalCount").Invoke(group,null);
            group.GetType().GetMethod("AddCustomSize").Invoke(group,new[]{size});
            var view=EditorWindow.GetWindow(assembly.GetType("UnityEditor.GameView"));
            view.GetType().GetProperty("selectedSizeIndex",BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance).SetValue(view,count);
        }
        static void Tick()
        {
            if(EditorApplication.timeSinceStartup-SessionState.GetFloat(Key+".start",0)>1900){Finish(1);return;}
            var result=PlayerRegressionSuite.Latest;
            if(result==null||result.status=="RUNNING")return;
            string output=Path.GetFullPath("../Verification/Evidence/Regression/Editor");Directory.CreateDirectory(output);
            foreach(var file in Directory.GetFiles(PlayerRegressionSuite.Output))File.Copy(file,Path.Combine(output,Path.GetFileName(file)),true);
            Finish(result.status=="PASS_NATIVE_REGRESSION"?0:1);
        }
        static void Finish(int code){SessionState.EraseBool(Key);EditorApplication.update-=Tick;EditorApplication.Exit(code);}
    }
}
#endif
