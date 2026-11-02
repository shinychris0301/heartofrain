package com.heartoftherain.launch99;

import android.app.Activity;
import android.app.Application;
import android.annotation.TargetApi;
import android.content.ContentProvider;
import android.content.ContentValues;
import android.content.pm.ApplicationInfo;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.SystemClock;
import android.util.Log;
import android.view.View;
import android.view.ViewGroup;
import android.widget.FrameLayout;
import java.lang.ref.WeakReference;

/** Single native splash handoff; no timers, Activity replacement or player data. */
public final class LaunchCurtain99 extends ContentProvider {
    private static volatile boolean logoReady;
    private static volatile WeakReference<Activity> player = new WeakReference<>(null);
    private static View curtain;

    private static void trace(Activity activity, String stage) {
        if ((activity.getApplicationInfo().flags & ApplicationInfo.FLAG_DEBUGGABLE) != 0)
            Log.i("HOTR99", "stage=" + stage + " uptimeMs=" + SystemClock.uptimeMillis());
    }

    @Override public boolean onCreate() {
        Application application = (Application)getContext().getApplicationContext();
        application.registerActivityLifecycleCallbacks(new Application.ActivityLifecycleCallbacks() {
            @Override public void onActivityStarted(Activity activity) {
                if (!activity.getClass().getName().equals("com.unity3d.player.UnityPlayerActivity")) return;
                if (player.get() == activity && curtain != null && curtain.getParent() != null) return;
                Activity previous = player.get();
                if (previous != null && previous != activity) remove(previous);
                player = new WeakReference<>(activity);
                if (logoReady) return;
                // Unity installs its content in onCreate. Register after that,
                // before its first draw. On Android12+ the system has already
                // shown the icon: retain that very view instead of drawing a
                // second independently sized copy over the player surface.
                if (Build.VERSION.SDK_INT >= 31) {
                    Api31.install(activity);
                    return;
                }
                FrameLayout cover = new FrameLayout(activity);
                cover.setClickable(true);
                cover.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO_HIDE_DESCENDANTS);
                int resource = activity.getResources().getIdentifier("hotr_start_background99", "drawable", activity.getPackageName());
                if (resource == 0) { Log.e("HOTR99", "Native startup icon resource is missing"); return; }
                // API26-30 use the exact starting-window drawable, including
                // its geometry. There is no separate resize or clipping pass.
                cover.setBackgroundResource(resource);
                curtain = cover;
                activity.addContentView(cover, new ViewGroup.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
                trace(activity, "native_icon_curtain_installed");
            }
            @Override public void onActivityDestroyed(Activity activity) {
                if (player.get() == activity) { remove(activity); player.clear(); }
            }
            @Override public void onActivityCreated(Activity activity, Bundle state) { }
            @Override public void onActivityResumed(Activity activity) { }
            @Override public void onActivityPaused(Activity activity) { }
            @Override public void onActivityStopped(Activity activity) { }
            @Override public void onActivitySaveInstanceState(Activity activity, Bundle state) { }
        });
        return true;
    }

    private static void remove(Activity activity) {
        View current = curtain; curtain = null;
        if (Build.VERSION.SDK_INT >= 31 && Api31.remove(current)) {
            trace(activity, "platform_splash_removed");
            return;
        }
        if (current != null && current.getParent() instanceof ViewGroup) {
            ((ViewGroup)current.getParent()).removeView(current);
            trace(activity, "native_icon_curtain_removed");
        }
    }

    // Keep framework API31 types out of the API26-30 execution path. The
    // platform listener hands ownership of its actual splash view to us;
    // remove() releases it after Unity submits the real loading artwork.
    @TargetApi(31)
    private static final class Api31 {
        static void install(Activity activity) {
            activity.getSplashScreen().setOnExitAnimationListener(view -> {
                if (player.get() != activity || activity.isDestroyed()) {
                    view.remove();
                    return;
                }
                curtain = view;
                trace(activity, "platform_splash_exit_retained");
                if (logoReady) releaseOnNextFrame(activity, view);
            });
            trace(activity, "platform_splash_listener_installed");
        }

        static boolean remove(View view) {
            if (!(view instanceof android.window.SplashScreenView)) return false;
            ((android.window.SplashScreenView)view).remove();
            return true;
        }
    }

    private static void releaseOnNextFrame(Activity activity, View current) {
        current.postOnAnimation(() -> {
            if (player.get() == activity && curtain == current) remove(activity);
        });
    }

    @Override public Bundle call(String method, String argument, Bundle extras) {
        if (!"logo_frame_submitted99".equals(method)) return super.call(method, argument, extras);
        logoReady = true;
        Activity activity = player.get();
        if (activity != null) activity.runOnUiThread(() -> {
            trace(activity, "unity_logo_frame_signal");
            View current = curtain;
            if (current != null) releaseOnNextFrame(activity, current);
        });
        Bundle result = new Bundle(); result.putBoolean("accepted", true); return result;
    }
    // Non-exported provider is used only for the minifier-safe same-app signal.
    @Override public Cursor query(Uri uri, String[] projection, String selection, String[] arguments, String order) { return null; }
    @Override public String getType(Uri uri) { return null; }
    @Override public Uri insert(Uri uri, ContentValues values) { return null; }
    @Override public int delete(Uri uri, String selection, String[] arguments) { return 0; }
    @Override public int update(Uri uri, ContentValues values, String selection, String[] arguments) { return 0; }
}
