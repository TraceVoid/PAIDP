import React, { useState, useEffect } from 'react';
import {
  Container,
  Box,
  AppBar,
  Toolbar,
  Typography,
  TextField,
  Button,
  Card,
  CardContent,
  Grid,
  Alert,
  CircularProgress,
  Chip,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tab,
  Tabs
} from '@mui/material';
import {
  Security,
  Warning,
  CheckCircle,
  Block,
  TrendingUp,
  Assessment
} from '@mui/icons-material';
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const COLORS = ['#f44336', '#ff9800', '#4caf50'];

function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [currentTab, setCurrentTab] = useState(0);
  
  // Login/Register
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLogin, setIsLogin] = useState(true);
  
  // Analysis
  const [text, setText] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  
  // History & Stats
  const [history, setHistory] = useState([]);
  const [stats, setStats] = useState(null);
  const [loadingData, setLoadingData] = useState(false);
  
  // Dialog
  const [detailDialog, setDetailDialog] = useState(false);
  const [selectedLog, setSelectedLog] = useState(null);

  useEffect(() => {
    if (token) {
      loadHistory();
      loadStats();
    }
  }, [token]);

  const handleAuth = async () => {
    try {
      setError(null);
      
      if (isLogin) {
        // Login
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);
        
        const response = await axios.post(`${API_URL}/token`, formData);
        const accessToken = response.data.access_token;
        
        localStorage.setItem('token', accessToken);
        setToken(accessToken);
      } else {
        // Register
        const response = await axios.post(`${API_URL}/register`, {
          username,
          email,
          password
        });
        const accessToken = response.data.access_token;
        
        localStorage.setItem('token', accessToken);
        setToken(accessToken);
      }
      
      setUsername('');
      setEmail('');
      setPassword('');
    } catch (err) {
      setError(err.response?.data?.detail || 'Authentication failed');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setHistory([]);
    setStats(null);
    setResult(null);
  };

  const handleAnalyze = async () => {
    if (!text.trim()) {
      setError('Please enter text to analyze');
      return;
    }
    
    try {
      setAnalyzing(true);
      setError(null);
      
      const response = await axios.post(
        `${API_URL}/analyze`,
        { text },
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );
      
      setResult(response.data);
      setText('');
      
      // Refresh data
      loadHistory();
      loadStats();
    } catch (err) {
      setError(err.response?.data?.detail || 'Analysis failed');
    } finally {
      setAnalyzing(false);
    }
  };

  const loadHistory = async () => {
    try {
      setLoadingData(true);
      const response = await axios.get(`${API_URL}/history?limit=100`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      setHistory(response.data.logs);
    } catch (err) {
      console.error('Failed to load history:', err);
    } finally {
      setLoadingData(false);
    }
  };

  const loadStats = async () => {
    try {
      const response = await axios.get(`${API_URL}/stats`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      setStats(response.data);
    } catch (err) {
      console.error('Failed to load stats:', err);
    }
  };

  const getActionIcon = (action) => {
    switch (action) {
      case 'block':
        return <Block color="error" />;
      case 'alert':
        return <Warning color="warning" />;
      case 'allow':
        return <CheckCircle color="success" />;
      default:
        return null;
    }
  };

  const getActionColor = (action) => {
    switch (action) {
      case 'block':
        return 'error';
      case 'alert':
        return 'warning';
      case 'allow':
        return 'success';
      default:
        return 'default';
    }
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString();
  };

  // Si no hay token, mostrar login/register
  if (!token) {
    return (
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
        }}
      >
        <Card sx={{ maxWidth: 400, width: '100%', m: 2 }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
              <Security sx={{ fontSize: 40, color: 'primary.main', mr: 2 }} />
              <Typography variant="h4" component="h1">
                PAIDP
              </Typography>
            </Box>
            
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              AI-Powered Threat Detection Platform
            </Typography>

            <Box component="form" onSubmit={(e) => { e.preventDefault(); handleAuth(); }}>
              <TextField
                fullWidth
                label="Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                margin="normal"
                required
              />
              
              {!isLogin && (
                <TextField
                  fullWidth
                  label="Email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  margin="normal"
                  required
                />
              )}
              
              <TextField
                fullWidth
                label="Password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                margin="normal"
                required
              />

              {error && (
                <Alert severity="error" sx={{ mt: 2 }}>
                  {error}
                </Alert>
              )}

              <Button
                fullWidth
                variant="contained"
                size="large"
                type="submit"
                sx={{ mt: 3 }}
              >
                {isLogin ? 'Login' : 'Register'}
              </Button>

              <Button
                fullWidth
                onClick={() => {
                  setIsLogin(!isLogin);
                  setError(null);
                }}
                sx={{ mt: 1 }}
              >
                {isLogin ? 'Need an account? Register' : 'Have an account? Login'}
              </Button>
            </Box>
          </CardContent>
        </Card>
      </Box>
    );
  }

  // Dashboard principal
  return (
    <Box sx={{ minHeight: '100vh', bgcolor: '#f5f5f5' }}>
      <AppBar position="static">
        <Toolbar>
          <Security sx={{ mr: 2 }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            PAIDP Dashboard
          </Typography>
          <Button color="inherit" onClick={handleLogout}>
            Logout
          </Button>
        </Toolbar>
      </AppBar>

      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Tabs value={currentTab} onChange={(e, v) => setCurrentTab(v)} sx={{ mb: 3 }}>
          <Tab label="Analyze" icon={<Assessment />} iconPosition="start" />
          <Tab label="History" icon={<TrendingUp />} iconPosition="start" />
        </Tabs>

        {currentTab === 0 && (
          <>
            {/* Stats Cards */}
            {stats && (
              <Grid container spacing={3} sx={{ mb: 4 }}>
                <Grid item xs={12} sm={6} md={3}>
                  <Card>
                    <CardContent>
                      <Typography color="text.secondary" gutterBottom>
                        Total Analyses
                      </Typography>
                      <Typography variant="h4">
                        {stats.total_analyses}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Card>
                    <CardContent>
                      <Typography color="text.secondary" gutterBottom>
                        Blocked
                      </Typography>
                      <Typography variant="h4" color="error">
                        {stats.blocked}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Card>
                    <CardContent>
                      <Typography color="text.secondary" gutterBottom>
                        Alerts
                      </Typography>
                      <Typography variant="h4" color="warning.main">
                        {stats.alerted}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Card>
                    <CardContent>
                      <Typography color="text.secondary" gutterBottom>
                        Allowed
                      </Typography>
                      <Typography variant="h4" color="success.main">
                        {stats.allowed}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            )}

            {/* Analysis Section */}
            <Card sx={{ mb: 4 }}>
              <CardContent>
                <Typography variant="h5" gutterBottom>
                  Analyze Text
                </Typography>
                
                <TextField
                  fullWidth
                  multiline
                  rows={6}
                  placeholder="Enter text to analyze for threats..."
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  sx={{ mb: 2 }}
                />

                <Button
                  variant="contained"
                  size="large"
                  onClick={handleAnalyze}
                  disabled={analyzing || !text.trim()}
                  startIcon={analyzing ? <CircularProgress size={20} /> : <Security />}
                >
                  {analyzing ? 'Analyzing...' : 'Analyze'}
                </Button>

                {error && (
                  <Alert severity="error" sx={{ mt: 2 }}>
                    {error}
                  </Alert>
                )}
              </CardContent>
            </Card>

            {/* Result */}
            {result && (
              <Card>
                <CardContent>
                  <Typography variant="h5" gutterBottom>
                    Analysis Result
                  </Typography>
                  
                  <Grid container spacing={2}>
                    <Grid item xs={12} md={6}>
                      <Paper sx={{ p: 2 }}>
                        <Typography variant="subtitle2" color="text.secondary">
                          Action
                        </Typography>
                        <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                          {getActionIcon(result.action)}
                          <Chip
                            label={result.action.toUpperCase()}
                            color={getActionColor(result.action)}
                            sx={{ ml: 1 }}
                          />
                        </Box>
                      </Paper>
                    </Grid>
                    
                    <Grid item xs={12} md={6}>
                      <Paper sx={{ p: 2 }}>
                        <Typography variant="subtitle2" color="text.secondary">
                          Threat Score
                        </Typography>
                        <Typography variant="h4" sx={{ mt: 1 }}>
                          {(result.score * 100).toFixed(2)}%
                        </Typography>
                      </Paper>
                    </Grid>
                    
                    <Grid item xs={12}>
                      <Paper sx={{ p: 2 }}>
                        <Typography variant="subtitle2" color="text.secondary">
                          Analyzed Text
                        </Typography>
                        <Typography sx={{ mt: 1 }}>
                          {result.text}
                        </Typography>
                      </Paper>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            )}

            {/* Charts */}
            {stats && stats.total_analyses > 0 && (
              <Grid container spacing={3} sx={{ mt: 2 }}>
                <Grid item xs={12} md={6}>
                  <Card>
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        Action Distribution
                      </Typography>
                      <ResponsiveContainer width="100%" height={300}>
                        <PieChart>
                          <Pie
                            data={[
                              { name: 'Blocked', value: stats.blocked },
                              { name: 'Alerted', value: stats.alerted },
                              { name: 'Allowed', value: stats.allowed }
                            ]}
                            cx="50%"
                            cy="50%"
                            labelLine={false}
                            label={(entry) => `${entry.name}: ${entry.value}`}
                            outerRadius={80}
                            fill="#8884d8"
                            dataKey="value"
                          >
                            {COLORS.map((color, index) => (
                              <Cell key={`cell-${index}`} fill={color} />
                            ))}
                          </Pie>
                          <Tooltip />
                        </PieChart>
                      </ResponsiveContainer>
                    </CardContent>
                  </Card>
                </Grid>
                
                <Grid item xs={12} md={6}>
                  <Card>
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        Action Summary
                      </Typography>
                      <ResponsiveContainer width="100%" height={300}>
                        <BarChart
                          data={[
                            { name: 'Blocked', count: stats.blocked },
                            { name: 'Alerted', count: stats.alerted },
                            { name: 'Allowed', count: stats.allowed }
                          ]}
                        >
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="name" />
                          <YAxis />
                          <Tooltip />
                          <Bar dataKey="count" fill="#8884d8">
                            {COLORS.map((color, index) => (
                              <Cell key={`cell-${index}`} fill={color} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            )}
          </>
        )}

        {currentTab === 1 && (
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h5">
                  Analysis History
                </Typography>
                <Button onClick={loadHistory} disabled={loadingData}>
                  Refresh
                </Button>
              </Box>

              {loadingData ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                  <CircularProgress />
                </Box>
              ) : history.length === 0 ? (
                <Typography color="text.secondary" align="center" sx={{ p: 4 }}>
                  No analysis history yet
                </Typography>
              ) : (
                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Timestamp</TableCell>
                        <TableCell>Text</TableCell>
                        <TableCell>Score</TableCell>
                        <TableCell>Action</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {history.map((log) => (
                        <TableRow
                          key={log.id}
                          hover
                          onClick={() => {
                            setSelectedLog(log);
                            setDetailDialog(true);
                          }}
                          sx={{ cursor: 'pointer' }}
                        >
                          <TableCell>{formatTimestamp(log.timestamp)}</TableCell>
                          <TableCell>
                            {log.text.substring(0, 50)}
                            {log.text.length > 50 ? '...' : ''}
                          </TableCell>
                          <TableCell>{(log.score * 100).toFixed(2)}%</TableCell>
                          <TableCell>
                            <Chip
                              icon={getActionIcon(log.action)}
                              label={log.action}
                              color={getActionColor(log.action)}
                              size="small"
                            />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </CardContent>
          </Card>
        )}
      </Container>

      {/* Detail Dialog */}
      <Dialog
        open={detailDialog}
        onClose={() => setDetailDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Analysis Details</DialogTitle>
        <DialogContent>
          {selectedLog && (
            <Box>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Timestamp
              </Typography>
              <Typography paragraph>
                {formatTimestamp(selectedLog.timestamp)}
              </Typography>

              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Text
              </Typography>
              <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.100' }}>
                <Typography>{selectedLog.text}</Typography>
              </Paper>

              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    Threat Score
                  </Typography>
                  <Typography variant="h5">
                    {(selectedLog.score * 100).toFixed(2)}%
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    Action Taken
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    {getActionIcon(selectedLog.action)}
                    <Chip
                      label={selectedLog.action.toUpperCase()}
                      color={getActionColor(selectedLog.action)}
                      sx={{ ml: 1 }}
                    />
                  </Box>
                </Grid>
              </Grid>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailDialog(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default App;
