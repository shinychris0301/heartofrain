using UnityEngine;

namespace HeartOfTheRain.M05
{
    public enum BlastKind { Bomb, BombBomb, RocketBomb }

    /// <summary>Review effect footprints in cells; independent of sprite dimensions.</summary>
    public static class BlastPattern
    {
        public static bool Affected(int x, int y, int ox, int oy, int columns, int rows,
            BlastKind kind, int bombRadius = 2, int doubleRadius = 3, int bandHalfWidth = 1)
        {
            if (x<0 || x>=columns || y<0 || y>=rows) return false;
            int dx=Mathf.Abs(x-ox),dy=Mathf.Abs(y-oy);
            if (kind==BlastKind.RocketBomb) return dx<=bandHalfWidth || dy<=bandHalfWidth;
            return Mathf.Max(dx,dy)<=(kind==BlastKind.BombBomb?doubleRadius:bombRadius);
        }

        public static float Arrival(int x,int y,int ox,int oy,BlastKind kind,float cellsPerSecond,int bandHalfWidth=1)
        {
            float dx=Mathf.Abs(x-ox),dy=Mathf.Abs(y-oy);
            if (kind!=BlastKind.RocketBomb) return Mathf.Max(dx,dy)/Mathf.Max(1,cellsPerSecond);
            float alongRow=dy<=bandHalfWidth?dx:float.PositiveInfinity;
            float alongColumn=dx<=bandHalfWidth?dy:float.PositiveInfinity;
            return Mathf.Min(alongRow,alongColumn)/Mathf.Max(1,cellsPerSecond);
        }
    }
}
