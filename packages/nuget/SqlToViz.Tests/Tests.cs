using Xunit;
using System.Data;
using SqlToViz;
public class Tests {
 [Fact] public void Scalar()=>Assert.Equal("kpi",Preview.Recommend("SELECT 1",new[]{(IReadOnlyDictionary<string,object?>)new Dictionary<string,object?>{{"x",1}}}).ChartType);
 [Fact] public void TableInput(){var t=new DataTable();t.Columns.Add("a",typeof(string));t.Columns.Add("v",typeof(int));t.Rows.Add("A",1);t.Rows.Add("B",2);Assert.Equal("bar",Preview.Recommend("SELECT a,v",t).ChartType);}
 private sealed record Sale(string Category, decimal Amount);

 [Fact]
 public void TypedRowsMatchDataTable()
 {
     var rows = new[] { new Sale("A", 1.25m), new Sale("B", 2.5m) };
     var table = new DataTable();
     table.Columns.Add("category", typeof(string));
     table.Columns.Add("amount", typeof(decimal));
     foreach (var row in rows)
         table.Rows.Add(row.Category, row.Amount);

     const string sql = "SELECT category, amount";
     var plan = Preview.Recommend(sql, rows, row => new Dictionary<string, object?>
     {
         ["category"] = row.Category,
         ["amount"] = row.Amount,
     });
     Assert.Equal(Preview.Recommend(sql, table), plan);
     Assert.Equal("bar", plan.ChartType);
 }

 [Fact]
 public void InvalidTypedProjectionIsRejected()
 {
     Assert.Throws<ArgumentException>(() => Preview.Recommend("SELECT x", new[] { 1 }, _ => null!));
     Assert.Throws<ArgumentException>(() => Preview.Recommend("SELECT x", new[] { 1, 2 },
         value => new Dictionary<string, object?> { [$"column{value}"] = value }));
 }

 [Fact] public void Mad(){Assert.Equal(4,Statistics.Mad(new double?[]{1,2,3,4,100}).Outliers.Single().Index);Assert.Equal("zero_mad",Statistics.Mad(new double?[]{1,1,1,100}).Status);}
 [Fact] public void Temporal(){Assert.Equal("zero_baseline",Statistics.Temporal(new double?[]{0,10})[0].Status);Assert.Equal(.5,Statistics.Temporal(new double?[]{-10,-5})[0].RelativeChange);}
 [Fact] public void Pareto(){Assert.Equal("unknown_additivity",Statistics.Pareto(new double?[]{1,2}).Status);Assert.Single(Statistics.Pareto(new double?[]{20,80,0},.8,true).Items.Where(x=>x.Included));}
 [Fact] public void Pearson(){Assert.Equal(-1,Statistics.Pearson(new double?[]{1,2,3},new double?[]{3,2,1}).R!.Value,10);Assert.Equal("constant_column",Statistics.Pearson(new double?[]{1,1,1},new double?[]{1,2,3}).Status);}
}
