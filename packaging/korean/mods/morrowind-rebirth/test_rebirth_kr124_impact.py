"""No Bethesda/Rebirth assets: synthetic verification of KR12.4 impact scanner."""
import importlib.util
import pathlib
import struct
import tempfile
import unittest
import zipfile

SCRIPT=pathlib.Path(__file__).with_name("audit_kr124_release_deltas.py")
spec=importlib.util.spec_from_file_location("impact",SCRIPT)
impact=importlib.util.module_from_spec(spec)
spec.loader.exec_module(impact)

def sub(tag,txt):
    raw=txt.encode("utf-8")+b"\x00"
    return tag+struct.pack("<I",len(raw))+raw

def record(tag,body):
    return tag+struct.pack("<I",len(body))+b"\x00"*8+body

def info(iid,msg):
    return record(b"INFO",sub(b"INAM",iid)+sub(b"NAME",msg))

class ImpactTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path=pathlib.Path(tmp.name)/"v56.zip"

    def write_fixture(self,localized_overlap=False,alias_overlap=False):
        names=(
            ["Data Files/Morrowind Rebirth [Main].ESP",
             "Alternate Version/Morrowind Rebirth [Main].ESP"]
            + [f"Data Files/Morrowind Rebirth - {i} [Addon].ESP" for i in range(6)]
            + [f"Compability Patches/Compat_{i}.esm" for i in range(7)]
        )
        with zipfile.ZipFile(self.path,"w") as z:
            for i,p in enumerate(names):
                value=record(b"TES3",sub(b"HEDR","header"))
                if i==8:
                    value+=info("713021754425128647","You must join House Redoran")
                    value+=info("22806201441497819089","Report to Caius Cosades")
                    value+=info("6986172382590219429","Orders")
                if i==0 and localized_overlap:
                    value+=info("26689110631261324944","정@말# 제국 교단에 가입하는")
                z.writestr(p,value)
            for i in range(3):
                alias="마법부여사 아우데니안\t마법부여\n" if i==0 and alias_overlap else "고용\t서비스\n"
                z.writestr(f"Data Files/alias_{i}.top",alias)

    def test_nontranslatable_compatibility_records_held(self):
        self.write_fixture()
        r=impact.audit(self.path,verified_sha=False)
        self.assertEqual(r["plugin_count"],15)
        self.assertEqual(r["top_file_count"],3)
        self.assertEqual(r["owned_delta_candidates"],0)
        self.assertEqual(r["unmodified_english_compatibility_info_matches"],3)
        self.assertTrue(r["v56_unchanged"])

    def test_translated_overlap_flagged_not_patched(self):
        self.write_fixture(localized_overlap=True,alias_overlap=True)
        r=impact.audit(self.path,verified_sha=False)
        self.assertEqual(r["owned_delta_candidates"],3)
        self.assertEqual(len(r["kr124_top_alias_hits"]),1)
        self.assertTrue(r["v56_unchanged"])

    def test_non_pinned_archive_rejected(self):
        self.write_fixture()
        with self.assertRaisesRegex(ValueError,"Not the pinned Rebirth v56"):
            impact.audit(self.path,verified_sha=True)

if __name__=="__main__":
    unittest.main()
