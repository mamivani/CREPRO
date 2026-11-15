import React from 'react';
import { TouchableOpacity, Text, StyleSheet } from 'react-native';

interface ButtonProps {
  onPress: () => void;
  title: string;
  variant?: 'primary' | 'secondary' | 'danger';
  disabled?: boolean;
  testID?: string;
}

export const Button: React.FC<ButtonProps> = ({
  onPress,
  title,
  variant = 'primary',
  disabled = false,
  testID,
}) => {
  const style = [
    styles.button,
    styles[`button_${variant}`],
    disabled && styles.disabled,
  ];

  return (
    <TouchableOpacity
      style={style}
      onPress={onPress}
      disabled={disabled}
      testID={testID}
    >
      <Text style={[styles.text, styles[`text_${variant}`]]}>{title}</Text>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  button: {
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  button_primary: {
    backgroundColor: '#208AEF',
  },
  button_secondary: {
    backgroundColor: '#E8EAED',
  },
  button_danger: {
    backgroundColor: '#DC2626',
  },
  text: {
    fontSize: 16,
    fontWeight: '600',
  },
  text_primary: {
    color: '#FFFFFF',
  },
  text_secondary: {
    color: '#1F2937',
  },
  text_danger: {
    color: '#FFFFFF',
  },
  disabled: {
    opacity: 0.5,
  },
});
