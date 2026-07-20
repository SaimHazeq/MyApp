import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Save, KeyRound, Trash2 } from "lucide-react";
import { AppShell } from "../widgets/AppShell";
import { Button, Card, Field, Input, Select } from "../widgets/common";
import { ConfirmModal } from "../widgets/Modal";
import { useAuth } from "../state/AuthContext";
import { settingsService } from "../services/settingsService";
import { toast } from "../state/useToastStore";
import { ANIMATION_STYLES } from "../utils/constants";

export default function SettingsScreen() {
  const { user, refreshUser, logout } = useAuth();
  const navigate = useNavigate();

  const [fullName, setFullName] = useState(user?.full_name || "");
  const [prefs, setPrefs] = useState(user?.preferences || {});
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingPrefs, setSavingPrefs] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const saveProfile = async () => {
    setSavingProfile(true);
    try {
      await settingsService.updateProfile({ full_name: fullName });
      await refreshUser();
      toast.success("Profile updated.");
    } catch {
      toast.error("Couldn't update profile.");
    } finally {
      setSavingProfile(false);
    }
  };

  const savePrefs = async () => {
    setSavingPrefs(true);
    try {
      await settingsService.updatePreferences(prefs);
      await refreshUser();
      toast.success("Preferences saved.");
    } catch {
      toast.error("Couldn't save preferences.");
    } finally {
      setSavingPrefs(false);
    }
  };

  const changePassword = async () => {
    setChangingPassword(true);
    try {
      await settingsService.changePassword({ current_password: currentPassword, new_password: newPassword });
      setCurrentPassword("");
      setNewPassword("");
      toast.success("Password changed.");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Couldn't change password.");
    } finally {
      setChangingPassword(false);
    }
  };

  const deleteAccount = async () => {
    setDeleting(true);
    try {
      await settingsService.deleteAccount();
      logout();
      navigate("/login");
    } catch {
      toast.error("Couldn't delete account.");
      setDeleting(false);
    }
  };

  return (
    <AppShell title="Settings" subtitle="Account & preferences">
      <div className="max-w-2xl space-y-6">
        <Card className="p-6">
          <h3 className="font-display font-semibold mb-4">Profile</h3>
          <div className="space-y-4">
            <Field label="Full name">
              <Input value={fullName} onChange={(e) => setFullName(e.target.value)} />
            </Field>
            <Field label="Email">
              <Input value={user?.email || ""} disabled className="opacity-60" />
            </Field>
            <div className="flex justify-end">
              <Button onClick={saveProfile} loading={savingProfile}><Save size={16} /> Save profile</Button>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <h3 className="font-display font-semibold mb-4">Generation preferences</h3>
          <div className="space-y-4">
            <Field label="Default animation style">
              <Select value={prefs.default_animation_style || "3d_pixar"} onChange={(e) => setPrefs({ ...prefs, default_animation_style: e.target.value })}>
                {ANIMATION_STYLES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
              </Select>
            </Field>
            <label className="flex items-center justify-between p-3 rounded-xl bg-studio-surface2">
              <span className="text-sm">Auto-generate subtitles</span>
              <input type="checkbox" className="accent-marquee w-4 h-4"
                checked={Boolean(prefs.auto_generate_subtitles)}
                onChange={(e) => setPrefs({ ...prefs, auto_generate_subtitles: e.target.checked })} />
            </label>
            <label className="flex items-center justify-between p-3 rounded-xl bg-studio-surface2">
              <span className="text-sm">Email me when a movie finishes rendering</span>
              <input type="checkbox" className="accent-marquee w-4 h-4"
                checked={Boolean(prefs.email_notifications)}
                onChange={(e) => setPrefs({ ...prefs, email_notifications: e.target.checked })} />
            </label>
            <div className="flex justify-end">
              <Button onClick={savePrefs} loading={savingPrefs}><Save size={16} /> Save preferences</Button>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <h3 className="font-display font-semibold mb-4">Change password</h3>
          <div className="space-y-4">
            <Field label="Current password">
              <Input type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} />
            </Field>
            <Field label="New password" hint="At least 8 characters.">
              <Input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
            </Field>
            <div className="flex justify-end">
              <Button onClick={changePassword} loading={changingPassword} disabled={!currentPassword || newPassword.length < 8}>
                <KeyRound size={16} /> Update password
              </Button>
            </div>
          </div>
        </Card>

        <Card className="p-6 border-danger/30">
          <h3 className="font-display font-semibold mb-2 text-danger">Danger zone</h3>
          <p className="text-sm text-studio-muted mb-4">Deleting your account permanently removes all your movies and cannot be undone.</p>
          <Button variant="danger" onClick={() => setDeleteOpen(true)}><Trash2 size={16} /> Delete account</Button>
        </Card>
      </div>

      <ConfirmModal
        open={deleteOpen}
        title="Delete your account?"
        description="This permanently deletes your account and every movie you've created. This cannot be undone."
        confirmLabel="Delete my account"
        danger
        loading={deleting}
        onConfirm={deleteAccount}
        onClose={() => setDeleteOpen(false)}
      />
    </AppShell>
  );
}
