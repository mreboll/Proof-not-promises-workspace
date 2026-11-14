//@tag: issue-2129
//@library
namespace Lib
{
    public class ExternalWidget
    {
        public int Id { get; set; }
        public string Name { get; set; } = "";
    }
}
//@main
using MessagePack;
using MessagePack.Formatters;
using Lib;

namespace App
{
    [GeneratedMessagePackFormatter(SurrogateType = typeof(WidgetSurrogate))]
    public partial class ExternalWidgetFormatter : IMessagePackFormatter<ExternalWidget>
    {
    }

    public class WidgetSurrogate
    {
        [Key(3)] public int Id { get; set; }
        [Key(7)] public string Name { get; set; } = "";
    }
}
