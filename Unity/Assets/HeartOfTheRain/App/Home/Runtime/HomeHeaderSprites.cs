using System;
using UnityEngine;

namespace HeartOfTheRain.App.Home
{
    // Independent sprites share the approved texture; no regeneration or tint change.
    // The avatar pixels are outside Panel's UV rectangle and cannot show through it.
    public sealed class HomeHeaderSprites : IDisposable
    {
        public Sprite Panel { get; private set; }
        public Sprite DefaultAvatar { get; private set; }
        public Sprite Connector { get; private set; }

        public HomeHeaderSprites(Sprite source)
        {
            if(!source)throw new ArgumentNullException(nameof(source));
            if(source.packed&&source.packingRotation!=SpritePackingRotation.None)
                throw new InvalidOperationException("Home header must use an unrotated rectangular atlas entry.");
            Rect rect=source.textureRect;
            float split=Mathf.Round(rect.width*HomeHeaderGeometry.AvatarFraction);
            float portraitWidth=Mathf.Round(rect.width*HomeHeaderGeometry.DefaultPortraitFraction);
            float connectorWidth=Mathf.Round(rect.width*HomeHeaderGeometry.ConnectorFraction);
            DefaultAvatar=Slice(source,new Rect(rect.x,rect.y,portraitWidth,rect.height),"HomeHeaderDefaultAvatar");
            Panel=Slice(source,new Rect(rect.x+split,rect.y,rect.width-split,rect.height),"HomeHeaderPanel");
            Connector=Slice(source,new Rect(rect.x+split,rect.y,connectorWidth,rect.height),"HomeHeaderConnector");
        }
        private static Sprite Slice(Sprite source,Rect rect,string name)
        {
            var sprite=Sprite.Create(source.texture,rect,new Vector2(.5f,.5f),source.pixelsPerUnit,0,SpriteMeshType.FullRect);
            sprite.name=name;sprite.hideFlags=HideFlags.DontSave;return sprite;
        }
        public void Dispose()
        {
            if(Panel)UnityEngine.Object.Destroy(Panel);
            if(DefaultAvatar)UnityEngine.Object.Destroy(DefaultAvatar);
            if(Connector)UnityEngine.Object.Destroy(Connector);
            Panel=null;DefaultAvatar=null;Connector=null;
        }
    }
}
