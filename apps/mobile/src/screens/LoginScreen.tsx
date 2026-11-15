import React, { useState } from 'react';
import { View, Text, ScrollView, StyleSheet, ActivityIndicator, Alert } from 'react-native';
import { useRouter } from 'expo-router';
import { Button } from '@/components/Button';
import { Input } from '@/components/Input';
import { Card } from '@/components/Card';
import { useAuth } from '@/hooks/useAuth';

export default function LoginScreen() {
  const router = useRouter();
  const { loading, error, handleOAuthCallback } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleGoogleLogin = async () => {
    try {
      // In a real implementation, this would:
      // 1. Open WebBrowser with Google OAuth URL
      // 2. Listen for deep link callback
      // 3. Pass code to handleOAuthCallback
      Alert.alert('Coming Soon', 'Google OAuth integration with deep links');
    } catch (err) {
      Alert.alert('Login Failed', 'Unable to login with Google');
    }
  };

  const handleLocalLogin = async () => {
    if (!email.trim() || !password.trim()) {
      Alert.alert('Validation Error', 'Please enter email and password');
      return;
    }

    try {
      // In real implementation, call API endpoint for local auth
      Alert.alert('Demo Mode', 'Local login demo - replace with actual API call');
    } catch (err) {
      Alert.alert('Login Failed', 'Invalid credentials');
    }
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.title}>CREPRO</Text>
        <Text style={styles.subtitle}>Property Management</Text>

        <Card style={styles.card}>
          <Text style={styles.sectionTitle}>Sign In</Text>

          <Input
            label="Email"
            placeholder="your@email.com"
            value={email}
            onChangeText={setEmail}
            keyboardType="email-address"
            testID="login-email-input"
          />

          <Input
            label="Password"
            placeholder="••••••••"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            testID="login-password-input"
          />

          {error && <Text style={styles.error}>{error}</Text>}

          <Button
            title={loading ? 'Signing In...' : 'Sign In'}
            onPress={handleLocalLogin}
            disabled={loading}
            variant="primary"
            testID="login-submit-button"
          />

          <View style={styles.divider}>
            <View style={styles.line} />
            <Text style={styles.dividerText}>or</Text>
            <View style={styles.line} />
          </View>

          <Button
            title={loading ? 'Loading...' : 'Continue with Google'}
            onPress={handleGoogleLogin}
            disabled={loading}
            variant="secondary"
            testID="login-google-button"
          />
        </Card>

        {loading && (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color="#208AEF" />
          </View>
        )}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F9FAFB',
  },
  content: {
    flex: 1,
    padding: 20,
    justifyContent: 'center',
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#208AEF',
    textAlign: 'center',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 16,
    color: '#6B7280',
    textAlign: 'center',
    marginBottom: 24,
  },
  card: {
    marginVertical: 0,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 16,
    color: '#1F2937',
  },
  error: {
    color: '#DC2626',
    fontSize: 14,
    marginVertical: 8,
    textAlign: 'center',
  },
  divider: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 16,
  },
  line: {
    flex: 1,
    height: 1,
    backgroundColor: '#E5E7EB',
  },
  dividerText: {
    marginHorizontal: 12,
    color: '#9CA3AF',
    fontSize: 14,
  },
  loadingContainer: {
    marginTop: 20,
    alignItems: 'center',
  },
});
