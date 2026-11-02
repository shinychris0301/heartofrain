"""Source/privacy preparation checks only; no Unity, SDK or device invocation."""
from __future__ import annotations
import ast
import importlib.util
import json
from pathlib import Path
import re
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('payment_diag_preparer127',HERE/'prepare_payment_diagnostics127.py');prep=importlib.util.module_from_spec(spec);spec.loader.exec_module(prep)
HARNESS=(HERE/'PaymentDiagnostics127.cs').read_text('utf-8')

class PaymentDiagnosticSourcePrivacy127(unittest.TestCase):
    def test_python_source_syntax(self):
        ast.parse((HERE/'prepare_payment_diagnostics127.py').read_text('utf-8'))

    def test_exact_sdk_availability_signature_and_model(self):
        client=(prep.SDK/'RuStorePayClient.cs').read_text('utf-8-sig');model=(prep.SDK/'Model/PurchaseAvailabilityResult.cs').read_text('utf-8-sig')
        self.assertIn('PluginVersion = "11.1.0"',client)
        self.assertIn('GetPurchaseAvailability(Action<RuStoreError> onFailure, Action<PurchaseAvailabilityResult> onSuccess)',client)
        self.assertIn('public bool isAvailable;',model);self.assertIn('public RuStoreError cause;',model)

    def test_only_availability_sdk_operation(self):
        calls=re.findall(r'RuStorePayClient\.Instance\.(\w+)\s*\(',HARNESS)
        self.assertEqual(calls,['GetPurchaseAvailability'])
        for value in ('.Purchase(','.GetPurchase(','.GetPurchases(','.BeginVk(','.BeginVkSignin(','.CompleteVkSignin(','.WithAuthenticatedSession(','.RefreshProviders(','.Refresh(','.sdk-report', 'UnityWebRequest','HttpClient','AndroidJavaObject'):
            self.assertNotIn(value,HARNESS)

    def test_bootstrap_never_invokes_sdk_or_status(self):
        bootstrap=HARNESS.split('static void Bootstrap(){',1)[1].split('void Awake(){',1)[0]
        self.assertNotIn('QueryAvailability(',bootstrap);self.assertNotIn('ReadStatus(',bootstrap);self.assertNotIn('RuStorePayClient',bootstrap)
        self.assertIn('UNITY_ANDROID && DEVELOPMENT_BUILD && !UNITY_EDITOR',bootstrap)

    def test_actual_modal_cache_only_no_second_service(self):
        self.assertIn('var providers=Providers;',HARNESS);self.assertIn('VkSigninService?.VkSignin',HARNESS)
        self.assertIn('selected.interactable&&selected.IsInteractable()',HARNESS)
        self.assertNotIn('new ServerAccountService83',HARNESS)
        self.assertEqual(re.findall(r'GetField\("([^"]+)"',HARNESS),['flow'])

    def test_runtime_data_is_not_name_allowlist(self):
        names=set(prep.allowed_names());pattern=re.compile(r'[A-Za-z_][A-Za-z0-9_.]{0,95}')
        self.assertIn('CheckoutPaymentUnavailable',names);self.assertIn('RuStorePaySignatureException',names)
        for value in ('SECRET_SENSITIVE_12345','Bearer private-token','https://private.invalid/','7f6e5d4c3b2a1098','a'*400,'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJwcml2YXRlIn0.signature'):
            self.assertFalse(bool(pattern.fullmatch(value)) and value in names)
        self.assertIn('KnownNames.Contains(value)',HARNESS)

    def test_serialization_sanitizes_every_string_field(self):
        snapshot=HARNESS.split('class PaymentDiagnosticSnapshot127 {',1)[1].split('// This component',1)[0]
        declaration=snapshot.split('public string ',1)[1].split(';',1)[0]
        fields=re.findall(r'\b([a-zA-Z]\w*)\s*=',declaration)
        serializer=HARNESS.split('public static string Serialize(',1)[1].split('public static bool PrivacyChecks()',1)[0]
        self.assertEqual(len(fields),8)
        for field in fields:self.assertIn('value.'+field+'=',serializer)
        self.assertIn('result.Length>8192',serializer)
        self.assertNotIn('.description',HARNESS);self.assertNotIn('.ToString(',HARNESS);self.assertNotIn('Debug.Log',HARNESS)

    def test_native_builder_retains_guards_and_adds_real_privacy_test(self):
        builder=prep.builder().decode()
        self.assertIn('PaymentDiagnostics127.PrivacyChecks()',builder)
        self.assertIn('ActualDiagnosticSerializerPrivacyChecks127',builder)
        self.assertIn('PlayerSettings.Android.bundleVersionCode==127',builder)
        self.assertIn('AdvertisingBuild107.CombinedErrors126()',builder)
        self.assertIn('SdkVendorBindings125.ActualPackageErrors()',builder)
        self.assertIn('HOTR_RELEASE_SIGNING_PASSWORD',builder)
        self.assertIn('PlayerSettings.Android.keystorePass=""',builder)

    def test_final_builder_requires_real_source_bound_layout_report(self):
        builder=prep.builder(require_layout=True).decode()
        self.assertIn('SigninLayout127Verification.RequireAcceptedReport',builder)
        self.assertIn('HOTR_SIGNIN_LAYOUT127_REPORT',builder)
        self.assertIn('ActualSourceBoundSigninLayout127Accepted',builder)

    def test_copied_project_sources_are_only_three_dirs(self):
        source=(HERE/'prepare_payment_diagnostics127.py').read_text('utf-8')
        self.assertIn("for name in ('Assets','Packages','ProjectSettings'):shutil.copytree(SOURCE/name,project/name)",source)
        self.assertIn("set(original_changes)=={'ProjectSettings/ProjectSettings.asset','Assets/csc.rsp'}",source)
        self.assertIn("inventory(SOURCE)==before",source);self.assertIn("inventory(ROOT/'Unity')==main_before",source)

    def test_fixed_diagnostic_file_only(self):
        self.assertIn('FileName="PaymentDiagnostics127.json"',HARNESS)
        self.assertIn('Path.Combine(Application.persistentDataPath,FileName)',HARNESS)
        for forbidden in ('accessToken','refreshToken','CurrentAccess','PlayerId','authorizeUrl','developerPayload','purchaseId','invoiceId','username','bindingId'):
            self.assertNotIn(forbidden,HARNESS)

    def test_failed_local_read_is_persisted_before_sdk_dispatch(self):
        query=HARNESS.split('void QueryAvailability(){',1)[1].split('void Persist(){',1)[0]
        prefix=query.split('RuStore.PayClient.RuStorePayClient.Instance.GetPurchaseAvailability(',1)[0]
        self.assertIn('state.observation="LOCAL_READ_EXCEPTION";state.exceptionType=SafeException(failure);Persist();return;',prefix)

    def test_active_vk_button_precedes_inactive_destroy_scheduled_clone(self):
        fill=HARNESS.split('public void FillPrivateDiagnostic127(',1)[1]
        self.assertIn('if(!first)first=button;',fill)
        self.assertIn('if(button.gameObject.activeInHierarchy){currentButton=button;break;}',fill)
        self.assertIn('var selected=currentButton?currentButton:first;',fill)

if __name__=='__main__':unittest.main()
