# CREPRO Mobile App - Deployment & Build Commands

**Version**: 1.0.0  
**Last Updated**: November 8, 2026  
**Status**: Ready for Production

---

## Quick Start

### Prerequisites
1. Install Node.js 18+ (currently using v24.16.0)
2. Install npm 9+ (currently using v11.2.0)
3. For EAS builds: `npm install -g eas-cli`
4. For iOS: Access to macOS or EAS cloud service

### Setup
```bash
# Navigate to mobile app
cd apps/mobile

# Install dependencies (with legacy-peer-deps due to React version mismatch)
npm install --legacy-peer-deps

# Verify everything works
npm run lint
```

---

## Development

### Start Development Server
```bash
# Start Metro bundler and choose platform
npm start

# Or start with specific platform
npm start -- --android    # Start Android Emulator
npm start -- --ios        # Start iOS Simulator
npm start -- --web        # Start Web version
```

### Alternative Direct Launches
```bash
npm run android    # Direct Android Emulator
npm run ios        # Direct iOS Simulator
npm run web        # Web browser
```

---

## Testing

### Run Tests
```bash
# Run all tests once
npm test

# Run tests with coverage report
npm test:coverage

# Run tests in watch mode (re-run on file changes)
npm test:watch
```

### Expected Output
```
PASS  src/hooks/useAuth.test.ts
PASS  src/services/api.test.ts

Test Suites: 2 passed, 2 total
Tests:       X passed, X total
```

---

## Building for Production

### Prerequisites for Builds
1. EAS CLI installed: `npm install -g eas-cli`
2. GitHub account linked for EAS authentication
3. For Play Store: `google-play-release-key.jks` (or EAS signing)
4. For App Store: Apple Developer account (or EAS signing)

### Build Android APK
```bash
# Using EAS Build (recommended - cloud-based)
npm run build:android

# Output: APK file suitable for Play Store internal testing
# File: ~/EAS-builds/com.creprotech.mobile-production.apk
# Size: ~40-50 MB
# Time: 10-15 minutes
```

### Build iOS IPA
```bash
# Using EAS Build (macOS or cloud)
npm run build:ios

# For local build (macOS only)
eas build --platform ios --local

# Output: IPA file suitable for TestFlight/App Store
# File: ~/EAS-builds/com.creprotech.mobile-production.ipa
# Size: ~60-80 MB
# Time: 15-20 minutes
```

### Build Both Platforms
```bash
# Build Android and iOS in sequence
npm run build:android && npm run build:ios

# Or build in parallel
eas build --platform all
```

---

## App Store Submission

### Prerequisites
- [ ] Legal documents ready (PRIVACY_POLICY.md, TERMS_OF_SERVICE.md)
- [ ] App screenshots (2-5 per device)
- [ ] App description and keywords
- [ ] Privacy policy URL
- [ ] Support email
- [ ] App icon (1024x1024 PNG)
- [ ] Feature graphics (1024x500 PNG for Play Store)

### Submit to Google Play Store
```bash
# Step 1: Build APK
npm run build:android

# Step 2: Upload to Play Store (use CLI or web console)
npm run submit:android

# Or manual upload:
# 1. Go to https://play.google.com/console
# 2. Select app "CREPRO Mobile"
# 3. Create new release in "Internal testing" track
# 4. Upload APK from ~/EAS-builds/
# 5. Set version number: 1.0.0
# 6. Add release notes
# 7. Submit for review
```

### Submit to Apple App Store
```bash
# Step 1: Build IPA
npm run build:ios

# Step 2: Submit to TestFlight/App Store
npm run submit:ios

# Or manual upload:
# 1. Go to https://appstoreconnect.apple.com
# 2. Select app "CREPRO"
# 3. Create new version 1.0.0
# 4. Upload IPA from ~/EAS-builds/
# 5. Fill app information, keywords, category
# 6. Add privacy policy URL
# 7. Submit for review
```

---

## Environment Variables

### Development
```bash
# .env (not required, using defaults)
EXPO_PUBLIC_API_URL=http://localhost:8000
EXPO_PUBLIC_OAUTH_CLIENT_ID=your-client-id
```

### Production
```bash
# app.json (already configured)
EXPO_PUBLIC_API_URL=https://api.creprotech.com
EXPO_PUBLIC_OAUTH_CLIENT_ID=production-client-id
```

---

## Version Bumping

### For Play Store / App Store Release
```bash
# Update version in app.json
vi app.json

# Change version from 1.0.0 to 1.0.1 (or new version)
# Increment buildNumber as well

# Commit version bump
git add app.json
git commit -m "Bump version to 1.0.1"
git push origin main

# Then proceed with build and submission
```

### Version Format
- **Version**: Semantic versioning (1.0.0, 1.0.1, 1.1.0, 2.0.0)
- **Build Number**: Auto-increment (v1 → v2 → v3)
- Update both when submitting new build to stores

---

## Troubleshooting

### npm install Fails
```bash
# Clear cache and retry
rm -rf node_modules package-lock.json
npm install --legacy-peer-deps
```

### React/React Native Version Mismatch
```
Error: React 18.2.0 and React Native 0.88 version conflict
```

**Solution**: Use legacy peer dependencies flag
```bash
npm install --legacy-peer-deps
npm start -- --legacy-peer-deps
```

Future fix: Upgrade React to 19.x

### Expo/EAS Not Found
```bash
# Install EAS CLI globally
npm install -g eas-cli

# Initialize EAS in project (if not done)
cd apps/mobile
eas init --id 12345  # Use existing Expo project ID
```

### Biometric Auth Not Working
- Ensure native modules are linked
- Test on real device (biometric features require device)
- Check permissions in app.json are declared

### Offline Sync Not Queuing
- Check network state: `useOfflineSyncStore((s) => s.isOnline)`
- Verify SQLite database created: `./mobile.db` in app storage
- Check console logs for sync errors

### App Crashes on Launch
1. Check logs: `npm run dev -- --clear`
2. Clear app data on device
3. Rebuild: `npm run android` or `npm run ios`
4. Check for unhandled promise rejections

---

## Performance Profiling

### Check Bundle Size
```bash
# Build and analyze
eas build --platform android --analyze-build-output

# Output shows size breakdown by module
```

### Memory Profiling
```bash
# Launch with React DevTools
npm start -- --dev-client

# Connect React DevTools Profiler for memory analysis
```

### Network Requests
```bash
# Enable verbose logging
EXPO_DEBUG=true npm start
```

---

## Security Checklist

- [ ] No hardcoded secrets in code ✅
- [ ] OAuth tokens use SecureStore ✅
- [ ] API endpoints use HTTPS ✅
- [ ] Privacy policy accessible in app ✅
- [ ] Terms of service accessible in app ✅
- [ ] Permissions only requested when needed ✅
- [ ] No PII stored in SQLite ✅
- [ ] Offline sync queue encrypted ✅

---

## Success Criteria

### Build Success
- ✅ npm install completes without errors
- ✅ npm run lint passes all checks
- ✅ npm test runs and passes (if implemented)
- ✅ eas build completes APK/IPA generation
- ✅ App launches and authentication works

### Store Submission Success
- ✅ APK/IPA accepted by build system
- ✅ App metadata complete and reviewed
- ✅ Legal documents linked correctly
- ✅ Screenshots meet store requirements
- ✅ Privacy policy and terms publicly accessible
- ✅ App passes security and policy review
- ✅ App appears in store search results

### Production Deployment Success
- ✅ Users can download from Play Store / App Store
- ✅ App launches without crashes
- ✅ OAuth authentication works
- ✅ Offline sync functions correctly
- ✅ No crash reports in first 24 hours
- ✅ Performance metrics within targets

---

## Monitoring & Support

### Post-Launch Monitoring
```bash
# Check app crashes (requires Sentry/Crashlytics integration)
# Coming in Day 21+

# Monitor offline sync success rate
# Check SQLite database: SELECT COUNT(*) FROM sync_queue;

# Monitor app performance
# Check memory usage and startup time
```

### User Support
- Privacy Policy: In-app Settings menu
- Terms of Service: In-app Settings menu
- Bug Reports: GitHub Issues (internal)
- User Feedback: TBD (community portal)

---

## Next Steps (Days 21+)

1. **Photo Upload API**: Implement backend `/api/properties/{id}/photos` endpoint
2. **Push Notifications**: Complete Expo Notifications integration
3. **Analytics**: Add Mixpanel or Firebase Analytics
4. **Performance**: Profile and optimize startup time
5. **Accessibility**: Add a11y improvements
6. **Dark Mode**: Implement theme switching
7. **Internationalization**: Add i18n support
8. **CI/CD**: Automate builds on commit to main
9. **Crash Monitoring**: Add Sentry or Crashlytics
10. **App Updates**: Implement EAS Updates for OTA patching

---

## Useful Links

- **Expo Documentation**: https://docs.expo.dev
- **React Native Docs**: https://reactnative.dev
- **EAS Build**: https://eas.expo.dev
- **Play Store Console**: https://play.google.com/console
- **App Store Connect**: https://appstoreconnect.apple.com
- **GitHub Repo**: https://github.com/mamivani/CREPRO

---

**Questions?** Check DAYS_17-20_IMPLEMENTATION_GUIDE.md or create an issue on GitHub.
