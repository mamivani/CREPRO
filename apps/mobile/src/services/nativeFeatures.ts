import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, Alert } from 'react-native';
import * as Location from 'expo-location';
import * as LocalAuthentication from 'expo-local-authentication';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';

interface LocationCoordinates {
  latitude: number;
  longitude: number;
  accuracy: number;
}

export class NativeFeatures {
  // Geolocation
  static async requestLocationPermission(): Promise<boolean> {
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      return status === 'granted';
    } catch (error) {
      console.error('Location permission error:', error);
      return false;
    }
  }

  static async getCurrentLocation(): Promise<LocationCoordinates | null> {
    try {
      const hasPermission = await this.requestLocationPermission();
      if (!hasPermission) {
        throw new Error('Location permission denied');
      }

      const location = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.High,
      });

      return {
        latitude: location.coords.latitude,
        longitude: location.coords.longitude,
        accuracy: location.coords.accuracy || 0,
      };
    } catch (error) {
      console.error('Get location error:', error);
      return null;
    }
  }

  static async startLocationTracking(
    callback: (location: LocationCoordinates) => void,
    interval = 10000
  ): Promise<void> {
    try {
      const hasPermission = await this.requestLocationPermission();
      if (!hasPermission) {
        throw new Error('Location permission denied');
      }

      await Location.watchPositionAsync(
        {
          accuracy: Location.Accuracy.High,
          timeInterval: interval,
          distanceInterval: 100, // 100 meters
        },
        (location) => {
          callback({
            latitude: location.coords.latitude,
            longitude: location.coords.longitude,
            accuracy: location.coords.accuracy || 0,
          });
        }
      );
    } catch (error) {
      console.error('Location tracking error:', error);
    }
  }

  // Biometric Authentication
  static async isBiometricAvailable(): Promise<boolean> {
    try {
      const compatible = await LocalAuthentication.hasHardwareAsync();
      return compatible;
    } catch (error) {
      console.error('Biometric check error:', error);
      return false;
    }
  }

  static async getSupportedBiometrics(): Promise<LocalAuthentication.AuthenticationType[]> {
    try {
      return await LocalAuthentication.supportedAuthenticationTypesAsync();
    } catch (error) {
      console.error('Get biometrics error:', error);
      return [];
    }
  }

  static async authenticate(): Promise<boolean> {
    try {
      const isAvailable = await this.isBiometricAvailable();
      if (!isAvailable) {
        throw new Error('Biometric authentication not available');
      }

      const result = await LocalAuthentication.authenticateAsync({
        reason: 'Authenticate to access CREPRO',
        fallbackLabel: 'Use passcode',
        disableDeviceFallback: false,
      });

      return result.success;
    } catch (error) {
      console.error('Authentication error:', error);
      return false;
    }
  }

  static async enableBiometricAuth(): Promise<boolean> {
    try {
      const authenticated = await this.authenticate();
      if (!authenticated) {
        throw new Error('Biometric authentication failed');
      }

      // Store biometric preference
      return true;
    } catch (error) {
      console.error('Enable biometric error:', error);
      return false;
    }
  }

  static async verifyWithBiometric(): Promise<boolean> {
    try {
      return await this.authenticate();
    } catch (error) {
      console.error('Verification error:', error);
      return false;
    }
  }
}

// LocationScreen component
export default function LocationScreen() {
  const [location, setLocation] = useState<LocationCoordinates | null>(null);
  const [loading, setLoading] = useState(false);
  const [biometricAvailable, setBiometricAvailable] = useState(false);

  useEffect(() => {
    checkBiometric();
  }, []);

  const checkBiometric = async () => {
    const available = await NativeFeatures.isBiometricAvailable();
    setBiometricAvailable(available);
  };

  const handleGetLocation = async () => {
    try {
      setLoading(true);
      const loc = await NativeFeatures.getCurrentLocation();
      if (loc) {
        setLocation(loc);
        Alert.alert('Success', `Location: ${loc.latitude}, ${loc.longitude}`);
      } else {
        Alert.alert('Error', 'Could not get location');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleBiometricAuth = async () => {
    try {
      const success = await NativeFeatures.authenticate();
      if (success) {
        Alert.alert('Success', 'Biometric authentication successful');
      } else {
        Alert.alert('Failed', 'Biometric authentication failed');
      }
    } catch (error) {
      Alert.alert('Error', 'Biometric authentication error');
    }
  };

  return (
    <View style={styles.container}>
      <Card>
        <Text style={styles.title}>Location Services</Text>
        {location ? (
          <>
            <Text style={styles.info}>
              Latitude: {location.latitude.toFixed(6)}
            </Text>
            <Text style={styles.info}>
              Longitude: {location.longitude.toFixed(6)}
            </Text>
            <Text style={styles.info}>
              Accuracy: {Math.round(location.accuracy)} m
            </Text>
          </>
        ) : (
          <Text style={styles.info}>Location not yet retrieved</Text>
        )}
        {loading ? (
          <ActivityIndicator size="large" color="#208AEF" />
        ) : (
          <Button
            title="Get Current Location"
            onPress={handleGetLocation}
            variant="primary"
          />
        )}
      </Card>

      {biometricAvailable && (
        <Card>
          <Text style={styles.title}>Biometric Authentication</Text>
          <Text style={styles.info}>Biometric authentication available</Text>
          <Button
            title="Authenticate with Biometric"
            onPress={handleBiometricAuth}
            variant="primary"
          />
        </Card>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
    backgroundColor: '#F9FAFB',
  },
  title: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 12,
    color: '#1F2937',
  },
  info: {
    fontSize: 14,
    color: '#6B7280',
    marginVertical: 4,
  },
});
